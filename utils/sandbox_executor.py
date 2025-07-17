import subprocess
import tempfile
import os
from pathlib import Path

def run_tests_in_sandbox(files_to_write: dict, test_command: str) -> dict:
    """
    Creates a temporary directory, writes files to it, runs a test command,
    and captures the output.
    `files_to_write` is a dict of {"path/to/file.py": "content"}.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write all the provided files to the sandbox
        for rel_path, content in files_to_write.items():
            abs_path = Path(tmpdir) / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Execute the test command
        try:
            process = subprocess.run(
                test_command,
                shell=True,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120 # 2 minute timeout for tests
            )
            
            return {
                "passed": process.returncode == 0,
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "stdout": "",
                "stderr": "Error: Test execution timed out after 120 seconds."
            }
        except Exception as e:
            return {
                "passed": False,
                "stdout": "",
                "stderr": f"An unexpected error occurred during sandbox execution: {e}"
            }

if __name__ == "__main__":
    # Test sandbox execution with a simple Python pytest example
    test_code = """
import pytest
def add(a, b):
    return a + b
def test_add_success():
    assert add(2, 3) == 5
def test_add_failure():
    assert add(2, 3) == 6
"""
    files = {"tests/test_simple.py": test_code}
    command = "pytest"

    result = run_tests_in_sandbox(files, command)
    print("Sandbox execution result:")
    print(result)