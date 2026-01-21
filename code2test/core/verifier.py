"""
Code2Test Verifier

Executes and verifies generated tests, collecting results and triggering diagnosis.
"""

import subprocess
import logging
import json
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
        
        # Create temp file for JSON results
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = f.name
        
        try:
            # Run pytest with JSON report
            result = subprocess.run(
                [
                    "python", "-m", "pytest",
                    str(test_path),
                    f"--json-report",
                    f"--json-report-file={json_path}",
                    "-v",
                    "--tb=short",
                ],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            stdout = result.stdout
            stderr = result.stderr
            
            # Parse JSON report if available
            passed = []
            failed = []
            skipped = []
            
            if os.path.exists(json_path):
                try:
                    with open(json_path) as f:
                        report = json.load(f)
                    
                    for test in report.get("tests", []):
                        name = test.get("nodeid", "").split("::")[-1]
                        outcome = test.get("outcome", "")
                        
                        if outcome == "passed":
                            passed.append(name)
                        elif outcome == "failed":
                            failed.append(name)
                        elif outcome == "skipped":
                            skipped.append(name)
                            
                except Exception as e:
                    logger.warning(f"Failed to parse JSON report: {e}")
                    # Fall back to parsing stdout
                    passed, failed, skipped = self._parse_pytest_output(stdout)
            else:
                # Parse stdout for results
                passed, failed, skipped = self._parse_pytest_output(stdout)
            
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
            if os.path.exists(json_path):
                os.unlink(json_path)
    
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
