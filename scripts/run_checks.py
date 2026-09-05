"""Run real unit tests and package validation through one local/CI entrypoint."""

import argparse
import os
from pathlib import Path
import sys
import unittest

if __package__:
    from .validate_repo import validate
else:
    from validate_repo import validate


class _ExecutionResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_cases = 0
        self.skipped_cases = 0
        self.unverified_cases = 0
        self._active_case = None

    def startTest(self, test):
        self._active_case = test
        self._observed_non_skip = False
        self._observed_skip = False
        super().startTest(test)

    def addSkip(self, test, reason):
        if self._active_case is not None:
            self._observed_skip = True
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err):
        self._observed_non_skip = True
        super().addSubTest(test, subtest, err)

    def addSuccess(self, test):
        self._observed_non_skip = True
        super().addSuccess(test)

    def addFailure(self, test, err):
        self._observed_non_skip = True
        super().addFailure(test, err)

    def addError(self, test, err):
        self._observed_non_skip = True
        super().addError(test, err)

    def addExpectedFailure(self, test, err):
        self._observed_non_skip = True
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self._observed_non_skip = True
        super().addUnexpectedSuccess(test)

    def stopTest(self, test):
        # startTest/testsRun alone does not prove a non-skipped outcome. A
        # successful subtest does; skip-only subtests do not. Do not infer
        # execution from assertions that might occur outside these callbacks.
        if self._observed_non_skip:
            self.executed_cases += 1
        elif self._observed_skip:
            self.skipped_cases += 1
        else:
            self.unverified_cases += 1
        self._active_case = None
        super().stopTest(test)


def main(argv=None):
    """Return 1 for missing execution, failed tests, or invalid package; otherwise 0."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args(argv).root.resolve()
    errors = validate(root)
    discovered = executed = skipped = 0
    if not (root / "tests").is_dir():
        errors.append("0 tests discovered: tests directory is missing")
    else:
        previous_directory = Path.cwd()
        previous_path = sys.path[:]
        try:
            os.chdir(root)
            sys.path.insert(0, str(root))
            suite = unittest.TestLoader().discover(str(root / "tests"))
            discovered = suite.countTestCases()
            if discovered == 0:
                errors.append("0 tests discovered")
            else:
                result = unittest.TextTestRunner(verbosity=2, resultclass=_ExecutionResult).run(suite)
                skipped = result.skipped_cases
                executed = result.executed_cases
                if result.testsRun == 0:
                    errors.append("0 tests actually ran despite a non-empty discovered suite")
                elif executed <= 0:
                    errors.append("0 non-skipped test outcomes observed: all tests/subtests were skipped or execution is unverified")
                if result.unverified_cases:
                    errors.append(f"{result.unverified_cases} test cases have no observable outcome; cannot confirm execution")
                if not result.wasSuccessful():
                    errors.append("Unit tests failed; see their actual failure/error diagnostics above")
        except (ImportError, OSError) as exc:
            errors.append(f"Cannot discover or run unit tests: {exc}")
        finally:
            os.chdir(previous_directory)
            sys.path[:] = previous_path
    if errors:
        print(f"Checks failed ({len(errors)} problems):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Checks passed: {discovered} discovered, {executed} executed, {skipped} skipped; package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
