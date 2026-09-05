"""Exercise package validation by corrupting independent temporary repositories."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.validate_repo import main, validate


class RepositoryValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "skills" / "sample-skill"
        self.write("README.md", "# Package\n[Skill](skills/sample-skill/SKILL.md)\n")
        self.write("evals/README.md", "# Evaluations\n")
        self.write("skills/sample-skill/SKILL.md", "---\nname: sample-skill\ndescription: A useful skill.\n---\n# Skill\n")
        self.write("skills/sample-skill/agents/openai.yaml", 'interface:\n  display_name: Sample skill\n  short_description: "A useful description with enough characters"\n  default_prompt: "Use $sample-skill to verify the project."\n')
        self.write("skills/sample-skill/assets/arbiter.example.toml", 'id = "owner"\nrisk = "high"\npaths = ["src/**"]\ninvariant = "Only the owner writes."\nread = ["docs/not-in-this-package.md"]\nforbid = []\nchecks = ["check:owner"]\n')
        self.json("evals/cases.json", {"instruction": "Run independently.", "cases": [{"id": "first", "request": "Assess this receipt."}]})
        self.json("evals/rubric.json", {"cases": [{"id": "first", "must": ["Reject zero tests."], "must_not": []}]})

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def json(self, relative, value):
        self.write(relative, json.dumps(value, ensure_ascii=False))

    def cases(self, value):
        self.json("evals/cases.json", {"cases": value})

    def rubric(self, value):
        self.json("evals/rubric.json", {"cases": value})

    def assert_problem(self, text):
        errors = validate(self.root)
        self.assertTrue(errors, "Invalid package was reported as valid")
        self.assertIn(text, "\n".join(errors))

    def test_valid_package_allows_empty_forbid_and_virtual_project_paths(self):
        self.assertEqual([], validate(self.root))

    def test_missing_root_is_reported(self):
        self.assertTrue(validate(self.root / "missing"))

    def test_required_readmes_are_checked(self):
        for filename in ("README.md", "evals/README.md"):
            with self.subTest(filename=filename):
                path = self.root / filename
                original = path.read_text(encoding="utf-8")
                path.unlink()
                self.assert_problem(filename)
                path.write_text(original, encoding="utf-8")

    def test_no_skills_is_rejected(self):
        (self.skill / "SKILL.md").unlink()
        self.assert_problem("No skills/*/SKILL.md")

    def test_frontmatter_missing_or_malformed_is_rejected(self):
        for value in ("# No metadata", "---\nname: [\n---", "---\nname: sample-skill", "---\n- sequence\n---", "---\n!!python/object:builtins.list {}\n---"):
            with self.subTest(value=value):
                self.write("skills/sample-skill/SKILL.md", value)
                self.assert_problem("SKILL.md")

    def test_name_and_description_are_validated(self):
        for name, description in (("different", "Good"), ("Sample-skill", "Good"), ("sample--skill", "Good"), ("a" * 65, "Good"), (42, "Good"), ("sample-skill", ""), ("sample-skill", 123), ("sample-skill", None)):
            with self.subTest(name=name, description=description):
                # JSON scalars are also valid YAML scalars.
                self.write("skills/sample-skill/SKILL.md", f"---\nname: {json.dumps(name)}\ndescription: {json.dumps(description)}\n---\n")
                self.assert_problem("SKILL.md")

    def test_missing_interface_file_is_rejected(self):
        (self.skill / "agents/openai.yaml").unlink()
        self.assert_problem("agents/openai.yaml")

    def test_interface_yaml_must_be_mapping(self):
        for value in ("interface: [", "[]", "interface: []", "{}"):
            with self.subTest(value=value):
                self.write("skills/sample-skill/agents/openai.yaml", value)
                self.assert_problem("openai.yaml")

    def test_interface_required_fields_and_prompt_token_are_validated(self):
        valid = {"display_name": "Sample", "short_description": "A" * 25, "default_prompt": "Use $sample-skill."}
        for key, value in (("display_name", ""), ("display_name", None), ("short_description", "A" * 24), ("short_description", "A" * 65), ("short_description", 1), ("default_prompt", "Use $sample-skill-extra"), ("default_prompt", "Use sample-skill"), ("default_prompt", None)):
            with self.subTest(key=key, value=value):
                data = valid | {key: value}
                self.write("skills/sample-skill/agents/openai.yaml", json.dumps({"interface": data}))
                self.assert_problem(key)

    def test_description_length_boundaries_and_default_policy_are_allowed(self):
        for length in (25, 64):
            with self.subTest(length=length):
                self.write("skills/sample-skill/agents/openai.yaml", json.dumps({"interface": {"display_name": "名字", "short_description": "字" * length, "default_prompt": "使用 $sample-skill。"}}))
                self.assertEqual([], validate(self.root))

    def test_missing_or_invalid_toml_is_rejected(self):
        target = self.skill / "assets/arbiter.example.toml"
        target.unlink()
        self.assert_problem("arbiter.example.toml")
        target.write_text("id = [", encoding="utf-8")
        self.assert_problem("arbiter.example.toml")

    def test_toml_field_types_and_required_lists_are_checked(self):
        path = self.skill / "assets/arbiter.example.toml"
        valid = path.read_text(encoding="utf-8")
        for before, after in (('id = "owner"', 'id = 42'), ('risk = "high"', 'risk = ""'), ('invariant = "Only the owner writes."', 'invariant = []'), ('paths = ["src/**"]', 'paths = []'), ('paths = ["src/**"]', 'paths = [1]'), ('read = ["docs/not-in-this-package.md"]', 'read = "docs.md"'), ('forbid = []', 'forbid = [false]'), ('checks = ["check:owner"]', 'checks = []')):
            with self.subTest(after=after):
                path.write_text(valid.replace(before, after), encoding="utf-8")
                self.assert_problem("arbiter.example.toml")

    def test_broken_markdown_link_is_rejected(self):
        self.write("README.md", "[Broken](missing.md#section)\n")
        self.assert_problem("missing.md")

    def test_links_from_nested_markdown_are_relative_to_file(self):
        self.write("skills/sample-skill/SKILL.md", (self.skill / "SKILL.md").read_text(encoding="utf-8") + "[Guide](references/guide.md)\n")
        self.assert_problem("references/guide.md")
        self.write("skills/sample-skill/references/guide.md", "# Guide\n")
        self.assertEqual([], validate(self.root))

    def test_external_anchors_code_fences_and_inline_code_are_ignored(self):
        self.write("README.md", "[Website](https://example.com/missing) [Mail](mailto:test@example.com) [Anchor](#missing)\n```md\n[Example](missing.md)\n```\n~~~\n[Example](also-missing.md)\n~~~\n`[Example](inline-missing.md)`\n")
        self.assertEqual([], validate(self.root))

    def test_protocol_relative_url_is_external_even_when_local_path_is_missing(self):
        self.write("README.md", "[External](//example.com/no-local-file.md)\n")
        self.assertEqual([], validate(self.root))

    def test_encoded_path_angle_destination_and_reference_definition_are_supported(self):
        self.write("guide 中文.md", "# Guide")
        self.write("README.md", '[Guide](guide%20%E4%B8%AD%E6%96%87.md#unchecked)\n[Guide](<guide 中文.md> "title")\n[Guide][ref]\n[ref]: <guide 中文.md>\n')
        self.assertEqual([], validate(self.root))
        self.write("README.md", "[Guide][ref]\n[ref]: missing.md\n")
        self.assert_problem("missing.md")

    def test_images_are_checked(self):
        self.write("README.md", "![Image](missing.png)\n")
        self.assert_problem("missing.png")

    def test_link_traversal_and_absolute_paths_are_rejected(self):
        for target in ("../outside.md", "%2e%2e/outside.md", "/README.md", "C:/README.md"):
            with self.subTest(target=target):
                self.write("README.md", f"[Outside]({target})\n")
                self.assert_problem("outside repository")

    def test_unreadable_utf8_is_reported(self):
        (self.root / "README.md").write_bytes(b"\xff")
        self.assert_problem("README.md")

    def test_git_metadata_markdown_is_not_package_content(self):
        self.write(".git/internal.md", "[Missing](missing.md)")
        self.assertEqual([], validate(self.root))

    def test_bad_json_and_wrong_top_level_are_rejected(self):
        for path in ("evals/cases.json", "evals/rubric.json"):
            original = (self.root / path).read_text(encoding="utf-8")
            for content in ("{", "[]", "{}", '{"cases": null}', '{"cases": {}}'):
                with self.subTest(path=path, content=content):
                    self.write(path, content)
                    self.assert_problem(path)
            self.write(path, original)

    def test_missing_eval_files_are_rejected(self):
        for path in ("evals/cases.json", "evals/rubric.json"):
            original = (self.root / path).read_text(encoding="utf-8")
            (self.root / path).unlink()
            self.assert_problem(path)
            self.write(path, original)

    def test_empty_cases_and_rubric_are_rejected(self):
        self.cases([])
        self.rubric([])
        self.assert_problem("non-empty")

    def test_invalid_or_duplicate_case_ids_are_rejected(self):
        for rows in ([None], [{"request": "Go"}], [{"id": "", "request": "Go"}], [{"id": 42, "request": "Go"}], [{"id": "first", "request": "Go"}] * 2):
            with self.subTest(rows=rows):
                self.cases(rows)
                self.assert_problem("cases.json")

    def test_case_request_is_nonempty_text(self):
        for request in (None, "", "   ", 42, []):
            with self.subTest(request=request):
                self.cases([{"id": "first", "request": request}])
                self.assert_problem("request")

    def test_rubric_ids_must_match_without_duplicates(self):
        for rows in ([{"id": "other", "must": ["Do"], "must_not": []}], [{"id": "first", "must": ["Do"], "must_not": []}] * 2, [None]):
            with self.subTest(rows=rows):
                self.rubric(rows)
                self.assert_problem("rubric.json")

    def test_rubric_missing_and_extra_ids_are_reported(self):
        self.cases([{"id": "first", "request": "Go"}, {"id": "second", "request": "Go"}])
        self.rubric([{"id": "first", "must": ["Do"], "must_not": []}, {"id": "extra", "must": ["Do"], "must_not": []}])
        errors = "\n".join(validate(self.root))
        self.assertIn("second", errors)
        self.assertIn("extra", errors)

    def test_rubric_expectations_must_be_text_arrays(self):
        for key, value in (("must", []), ("must", "Do"), ("must", [None]), ("must", [""]), ("must_not", None), ("must_not", [42])):
            with self.subTest(key=key, value=value):
                row = {"id": "first", "must": ["Do"], "must_not": []} | {key: value}
                self.rubric([row])
                self.assert_problem(key)

    def test_many_unicode_eval_cases_work(self):
        self.cases([{"id": f"case-{index}", "request": "验证中文 🎯 ; DROP TABLE"} for index in range(10000)])
        self.rubric([{"id": f"case-{index}", "must": ["保留证据"], "must_not": []} for index in range(10000)])
        self.assertEqual([], validate(self.root))

    def test_cli_success_and_failure_are_explicit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["--root", str(self.root)])
        self.assertEqual(0, status)
        self.assertIn("passed", output.getvalue().lower())
        self.write("README.md", "[Bad](missing.md)")
        output = io.StringIO()
        with contextlib.redirect_stderr(output), contextlib.redirect_stdout(output):
            status = main(["--root", str(self.root)])
        self.assertEqual(1, status)
        self.assertIn("missing.md", output.getvalue())

    def test_cli_default_root_is_derived_from_script_not_working_directory(self):
        source = Path(__file__).resolve().parents[1] / "scripts/validate_repo.py"
        self.write("scripts/validate_repo.py", source.read_text(encoding="utf-8"))
        result = subprocess.run([sys.executable, str(self.root / "scripts/validate_repo.py")], cwd=self.root.parent, capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("passed", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
