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
from typing import Dict, List, Any, Optional
from pathlib import Path

from code2test.core.models import (
    TestFile,
    TestCase,
    TestStatus,
    VerificationResult,
    Diagnosis,
    TestFramework,
)

logger = logging.getLogger(__name__)


class TestVerifier:
    """
    Executes and verifies generated tests.
    
    Supports pytest execution with JSON result parsing.
    """
    
    def __init__(self, repo_path: str, timeout: int = 60):
        """
        Initialize verifier.
        
        Args:
            repo_path: Path to the repository root
            timeout: Timeout in seconds for test execution
        """
        self.repo_path = Path(repo_path)
        self.timeout = timeout
    
    def run_tests(self, test_file: TestFile) -> VerificationResult:
        """
        Execute tests and collect results.
        
        Args:
            test_file: TestFile to execute
            
        Returns:
            VerificationResult with pass/fail status
        """
        if test_file.framework == TestFramework.PYTEST:
            return self._run_pytest(test_file)
        else:
            logger.warning(f"Framework {test_file.framework} not fully supported")
            return self._run_pytest(test_file)
    
    def _run_pytest(self, test_file: TestFile) -> VerificationResult:
        """
        Run tests using pytest with JSON output.
        
        Args:
            test_file: TestFile to execute
            
        Returns:
            VerificationResult
        """
        test_path = self.repo_path / test_file.path
        
        # Check if file exists
        if not test_path.exists():
            # Write test file first
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(test_file.get_full_content())
        
        # Create temp file for JUnit XML results (built into pytest, no plugin needed)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            report_path = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    str(test_path),
                    f"--junitxml={report_path}",
                    "-v",
                    "--tb=short",
                    "-p", "no:cacheprovider",
                ],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            stdout = result.stdout
            stderr = result.stderr

            passed, failed, skipped = self._parse_junit_report(report_path)
            if not (passed or failed or skipped):
                passed, failed, skipped = self._parse_pytest_output(stdout)

            # pytest exit codes: 0 = all passed, 1 = failures, 2+ = collection/usage errors,
            # 5 = no tests collected. Anything but 0 means the file is not verified.
            if result.returncode != 0 and not failed:
                failed = [f"pytest exited with code {result.returncode}"]

            # Update test case statuses
            for tc in test_file.test_cases:
                if tc.name in passed:
                    tc.mark_passed()
                elif tc.name in failed:
                    tc.mark_failed(self._extract_failure_message(stdout, tc.name))
                elif tc.name in skipped:
                    tc.status = TestStatus.SKIPPED
            
            return VerificationResult(
                test_file_path=test_file.path,
                all_passed=len(failed) == 0,
                passed=passed,
                failed=failed,
                skipped=skipped,
                execution_time=0.0,  # Could parse from output
                stdout=stdout,
                stderr=stderr,
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {self.timeout}s")
            return VerificationResult(
                test_file_path=test_file.path,
                all_passed=False,
                failed=["TIMEOUT"],
                stderr=f"Test execution timed out after {self.timeout} seconds",
            )
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return VerificationResult(
                test_file_path=test_file.path,
                all_passed=False,
                failed=["ERROR"],
                stderr=str(e),
            )
            
        finally:
            # Cleanup temp file
            if os.path.exists(report_path):
                os.unlink(report_path)

    def _parse_junit_report(self, report_path: str) -> tuple[List[str], List[str], List[str]]:
        """Parse a pytest JUnit XML report into (passed, failed, skipped) test names."""
        passed, failed, skipped = [], [], []
        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            return passed, failed, skipped
        try:
            root = ET.parse(report_path).getroot()
        except ET.ParseError as e:
            logger.warning(f"Failed to parse JUnit report: {e}")
            return passed, failed, skipped

        for case in root.iter("testcase"):
            name = case.get("name", "").split("[")[0]
            if case.find("failure") is not None or case.find("error") is not None:
                failed.append(name)
            elif case.find("skipped") is not None:
                skipped.append(name)
            else:
                passed.append(name)
        return passed, failed, skipped
    
    def _parse_pytest_output(self, output: str) -> tuple[List[str], List[str], List[str]]:
        """
        Parse pytest output to extract test results.
        
        Args:
            output: pytest stdout
            
        Returns:
            Tuple of (passed, failed, skipped) test names
        """
        import re
        
        passed = []
        failed = []
        skipped = []
        
        # Match patterns like "test_name PASSED", "test_name FAILED"
        for line in output.split("\n"):
            # Look for test result lines
            match = re.search(r"(test_\w+)\s+(PASSED|FAILED|SKIPPED)", line)
            if match:
                name, status = match.groups()
                if status == "PASSED":
                    passed.append(name)
                elif status == "FAILED":
                    failed.append(name)
                elif status == "SKIPPED":
                    skipped.append(name)
        
        return passed, failed, skipped
    
    def _extract_failure_message(self, output: str, test_name: str) -> str:
        """
        Extract failure message for a specific test.
        
        Args:
            output: pytest stdout
            test_name: Name of the failing test
            
        Returns:
            Failure message or empty string
        """
        import re
        
        # Look for the failure section
        pattern = rf"{test_name}.*?(?:FAILED|ERROR).*?\n(.*?)(?=\n\w|$)"
        match = re.search(pattern, output, re.DOTALL)
        
        if match:
            return match.group(1).strip()[:500]
        
        return "Unknown failure"
    
    def write_test_file(self, test_file: TestFile) -> Path:
        """
        Write test file to disk.
        
        Args:
            test_file: TestFile to write
            
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
        
        Args:
            test_file: TestFile to validate
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            content = test_file.get_full_content()
            compile(content, test_file.path, "exec")
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
