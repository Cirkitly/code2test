"""
Code2Test Verifier

Executes and verifies generated tests, collecting results and triggering diagnosis.
"""

import subprocess
import logging
import sys
import xml.etree.ElementTree as ET
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

from code2test.core.models import (
    TestFile,
    TestStatus,
    VerificationResult,
    TestFramework,
)

logger = logging.getLogger(__name__)


@dataclass
class CaseResult:
    """Outcome of a single test as reported by pytest."""

    name: str              # test function name, without parametrization ids
    classname: str         # dotted module (and class) path, e.g. tests.calc.test_ops_add
    outcome: str           # passed | failed | skipped
    message: str = ""      # failure / error text


@dataclass
class PytestRun:
    """Result of one pytest invocation."""

    returncode: int
    cases: List[CaseResult] = field(default_factory=list)
    collection_error: str = ""   # error not tied to a test function (bad import, syntax)
    stdout: str = ""
    stderr: str = ""

    def names(self, outcome: str) -> List[str]:
        return [c.name for c in self.cases if c.outcome == outcome]

    @property
    def ok(self) -> bool:
        # pytest exit codes: 0 = all passed, 1 = failures, 2+ = errors, 5 = no tests collected
        return self.returncode == 0


class TestVerifier:
    """
    Executes and verifies generated tests.

    Runs pytest in a subprocess and reads its built-in JUnit XML report,
    so no extra pytest plugins are needed.
    """

    def __init__(self, repo_path: str, timeout: int = 60):
        """
        Args:
            repo_path: Path to repository root
            timeout: Timeout in seconds for test execution
        """
        self.repo_path = Path(repo_path)
        self.timeout = timeout

    def run_pytest(self, target: Path) -> PytestRun:
        """
        Run pytest on a file or directory from the repo root.

        The repo root (and ``src/`` if present) is put on PYTHONPATH so the code
        under test is importable, and the target repo's ``addopts`` are ignored so
        options like ``--cov`` can't fail the run when their plugin isn't installed.
        """
        env = os.environ.copy()
        extra_paths = [str(self.repo_path)]
        if (self.repo_path / "src").is_dir():
            extra_paths.append(str(self.repo_path / "src"))
        if env.get("PYTHONPATH"):
            extra_paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(extra_paths)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            report_path = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    str(target),
                    f"--junitxml={report_path}",
                    "-v",
                    "--tb=short",
                    "-p", "no:cacheprovider",
                    "-o", "addopts=",
                ],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            run = PytestRun(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
            self._parse_junit_report(report_path, run)
            if not run.cases and not run.collection_error and result.returncode not in (0, 5):
                run.collection_error = (result.stdout + "\n" + result.stderr).strip()[-3000:]
            return run
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {self.timeout}s")
            return PytestRun(
                returncode=-1,
                collection_error=f"Test execution timed out after {self.timeout} seconds",
            )
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)

    def run_tests(self, test_file: TestFile) -> VerificationResult:
        """
        Write a generated test file, execute it and update its test case statuses.

        Args:
            test_file: TestFile to execute

        Returns:
            VerificationResult with pass/fail status
        """
        if test_file.framework != TestFramework.PYTEST:
            logger.warning(f"Framework {test_file.framework} not fully supported, running with pytest")

        # Always write the current content so re-runs never verify a stale file
        test_path = self.write_test_file(test_file)
        run = self.run_pytest(test_path)

        passed, failed, skipped = run.names("passed"), run.names("failed"), run.names("skipped")
        messages = {c.name: c.message for c in run.cases if c.outcome == "failed"}

        # A collection error (bad import, syntax) fails the whole file: attribute it
        # to every test case so the repair loop sees the real error.
        known = set(passed) | set(failed) | set(skipped)
        file_error = None
        if not run.ok and run.returncode != 5 and not any(tc.name in known for tc in test_file.test_cases):
            file_error = run.collection_error or "pytest failed without reporting results"
            failed = [tc.name for tc in test_file.test_cases]

        # Anything but exit code 0 means the file is not verified
        if not run.ok and not failed:
            failed = [f"pytest exited with code {run.returncode}"]

        for tc in test_file.test_cases:
            if tc.name in failed:
                tc.mark_failed(file_error or messages.get(tc.name) or "Unknown failure")
            elif tc.name in passed:
                tc.mark_passed()
            elif tc.name in skipped:
                tc.status = TestStatus.SKIPPED

        return VerificationResult(
            test_file_path=test_file.path,
            all_passed=not failed,
            passed=passed,
            failed=failed,
            skipped=skipped,
            stdout=run.stdout,
            stderr=run.stderr or run.collection_error,
        )

    def _parse_junit_report(self, report_path: str, run: PytestRun) -> None:
        """Fill ``run`` from a pytest JUnit XML report."""
        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            return
        try:
            root = ET.parse(report_path).getroot()
        except ET.ParseError as e:
            logger.warning(f"Failed to parse JUnit report: {e}")
            return

        for case in root.iter("testcase"):
            name = case.get("name", "").split("[")[0]
            classname = case.get("classname", "")
            problem = case.find("failure")
            if problem is None:
                problem = case.find("error")
            if problem is not None:
                text = "\n".join(filter(None, [problem.get("message"), problem.text]))[-3000:]
                # Collection errors are reported as a pseudo test named after the module
                if not classname or "." in name:
                    run.collection_error = text
                else:
                    run.cases.append(CaseResult(name, classname, "failed", text))
            elif case.find("skipped") is not None:
                run.cases.append(CaseResult(name, classname, "skipped"))
            else:
                run.cases.append(CaseResult(name, classname, "passed"))

    def write_test_file(self, test_file: TestFile) -> Path:
        """
        Write test file to disk.

        Returns:
            Path to written file
        """
        test_path = self.repo_path / test_file.path
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_file.get_full_content())
        return test_path

    def validate_syntax(self, test_file: TestFile) -> tuple[bool, Optional[str]]:
        """
        Validate test file syntax without running.

        Returns:
            Tuple of (valid, error_message)
        """
        try:
            content = test_file.get_full_content()
            compile(content, test_file.path, "exec")
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
