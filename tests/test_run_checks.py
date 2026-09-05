"""Run the shared entrypoint against small real suites, never recursively itself."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_checks import main


class RunChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        files = {
            "README.md": "# Package\n",
            "evals/README.md": "# Evaluations\n",
            "evals/cases.json": json.dumps({"cases": [{"id": "one", "request": "Check"}]}),
            "evals/rubric.json": json.dumps({"cases": [{"id": "one", "must": ["Check"], "must_not": []}]}),
            "skills/sample/SKILL.md": "---\nname: sample\ndescription: Sample workflow.\n---\n",
            "skills/sample/agents/openai.yaml": 'interface:\n  display_name: Sample\n  short_description: "A useful description with enough characters"\n  default_prompt: "Use $sample."\n',
            "skills/sample/assets/arbiter.example.toml": 'id="one"\nrisk="high"\ninvariant="One owner"\npaths=["src/**"]\nread=[]\nforbid=[]\nchecks=["owner"]\n',
        }
        for relative, content in files.items():
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        scripts = self.root / "scripts"
        scripts.mkdir()
        source = Path(__file__).resolve().parents[1] / "scripts"
        for name in ("run_checks.py", "validate_repo.py"):
            shutil.copyfile(source / name, scripts / name)

    def suite(self, body):
        (self.root / "tests/test_sample.py").write_text("import unittest\n" + body, encoding="utf-8")

    def run_cli(self, use_default=False):
        args = [sys.executable, str(self.root / "scripts/run_checks.py")]
        if not use_default:
            args.extend(["--root", str(self.root)])
        return subprocess.run(args, cwd=self.root.parent, capture_output=True, text=True, encoding="utf-8", check=False)

    def test_empty_discovered_suite_cannot_pass(self):
        result = self.run_cli()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("0", result.stdout + result.stderr)

    def test_all_skipped_tests_cannot_pass(self):
        self.suite("class Sample(unittest.TestCase):\n    @unittest.skip('Unavailable')\n    def test_skip(self):\n        self.fail('Must not run')\n")
        result = self.run_cli()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("skipped", result.stdout + result.stderr)

    def test_real_assertion_failure_cannot_pass(self):
        self.suite("class Sample(unittest.TestCase):\n    def test_failure(self):\n        self.assertEqual(1, 2)\n")
        result = self.run_cli()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("1 != 2", result.stderr)

    def test_discovery_import_error_cannot_pass(self):
        self.suite("raise RuntimeError('broken import fixture')\n")
        result = self.run_cli()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("broken import fixture", result.stderr)

    def test_successful_suite_and_package_pass_from_another_working_directory(self):
        self.suite("class Sample(unittest.TestCase):\n    def test_success(self):\n        self.assertEqual(2 + 2, 4)\n")
        result = self.run_cli(use_default=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("1", result.stdout)
        self.assertIn("passed", result.stdout.lower())

    def test_skipped_subtest_does_not_hide_an_executed_passing_test(self):
        self.suite("class Sample(unittest.TestCase):\n    def test_mixed(self):\n        with self.subTest('skip'):\n            self.skipTest('One unavailable example')\n        with self.subTest('pass'):\n            self.assertEqual(2 + 2, 4)\n")
        result = self.run_cli()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_only_skipped_subtests_cannot_pass(self):
        self.suite("class Sample(unittest.TestCase):\n    def test_only_skips(self):\n        for value in (1, 2):\n            with self.subTest(value=value):\n                self.skipTest('Unavailable')\n                self.fail('Target assertion was never reached')\n")
        result = self.run_cli()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("skipped=2", result.stderr)
        self.assertIn("0", result.stderr)

    def test_class_and_module_skips_cannot_pass(self):
        for body in (
            "@unittest.skip('Unavailable class')\nclass Sample(unittest.TestCase):\n    def test_skip(self):\n        self.fail('Must not run')\n",
            "class Sample(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('Unavailable class fixture')\n    def test_skip(self):\n        self.fail('Must not run')\n",
            "raise unittest.SkipTest('Unavailable module')\n",
        ):
            with self.subTest(body=body):
                self.suite(body)
                result = self.run_cli()
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("skipped", result.stderr)

    def test_passing_suite_cannot_hide_broken_package(self):
        self.suite("class Sample(unittest.TestCase):\n    def test_success(self):\n        self.assertTrue(True)\n")
        (self.root / "README.md").write_text("[Missing](missing.md)", encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("missing.md", result.stdout + result.stderr)

    def test_claimed_nonempty_suite_with_zero_actual_execution_cannot_pass(self):
        class EmptyExecution(unittest.TestSuite):
            def countTestCases(self):
                return 1

        class NoObservableOutcome(unittest.TestCase):
            def runTest(self):
                self.fail("The custom runner never executes this method")

            def run(self, result):
                result.startTest(self)
                result.stopTest(self)
                return result

        for suite in (EmptyExecution(), unittest.TestSuite([NoObservableOutcome()])):
            with self.subTest(suite=type(suite).__name__):
                output = io.StringIO()
                with patch("scripts.run_checks.unittest.TestLoader.discover", return_value=suite), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    result = main(["--root", str(self.root)])
                self.assertEqual(1, result)
                self.assertIn("0", output.getvalue())

    def test_loader_suites_execute_and_restore_process_context(self):
        def success():
            self.assertEqual(Path.cwd(), self.root)

        def skipped():
            raise unittest.SkipTest("Temporary unavailable fixture")

        def failed():
            raise AssertionError("Actual assertion failure")

        for body, expected_status in ((success, 0), (skipped, 1), (failed, 1)):
            with self.subTest(body=body.__name__):
                suite = unittest.TestSuite([unittest.FunctionTestCase(body)])
                original_directory, original_path = Path.cwd(), sys.path[:]
                output = io.StringIO()
                with patch("scripts.run_checks.unittest.TestLoader.discover", return_value=suite), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    status = main(["--root", str(self.root)])
                self.assertEqual(expected_status, status, output.getvalue())
                self.assertEqual(original_directory, Path.cwd())
                self.assertEqual(original_path, sys.path)

    def test_discovery_error_is_a_clear_failure_and_restores_context(self):
        original_directory, original_path = Path.cwd(), sys.path[:]
        output = io.StringIO()
        with patch("scripts.run_checks.unittest.TestLoader.discover", side_effect=ImportError("discovery unavailable")), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main(["--root", str(self.root)])
        self.assertEqual(1, status)
        self.assertIn("discovery unavailable", output.getvalue())
        self.assertEqual(original_directory, Path.cwd())
        self.assertEqual(original_path, sys.path)

    def test_missing_test_directory_is_a_clear_failure(self):
        (self.root / "tests").rmdir()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main(["--root", str(self.root)])
        self.assertEqual(1, status)
        self.assertIn("tests directory is missing", output.getvalue())


if __name__ == "__main__":
    unittest.main()
