import subprocess
import tempfile
import os
import sys
from pathlib import Path

def run_tests_in_sandbox(files_to_write: dict, test_command: str) -> dict:
    """
    Creates a temporary directory with a virtual environment, installs project
    dependencies and pytest, writes files to it, runs a test command with
    the correct python path, and captures the output.
    `files_to_write` is a dict of {"path/to/file.py": "content"}.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # 1. Create a virtual environment
        venv_path = tmpdir_path / "venv"
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            stderr = e.stderr.decode() if hasattr(e, 'stderr') else "Timeout creating venv."
            return {"passed": False, "stdout": "", "stderr": f"Failed to create virtual environment: {stderr}"}

        # Determine python/pip executables for the venv
        pip_executable = str(venv_path / "bin" / "pip")
        if sys.platform == "win32":
            pip_executable = str(venv_path / "Scripts" / "pip.exe")

        # 2. Upgrade pip and install pytest
        try:
            subprocess.run([pip_executable, "install", "--upgrade", "pip"], check=True, capture_output=True, timeout=60)
            subprocess.run([pip_executable, "install", "pytest"], check=True, capture_output=True, timeout=120)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
             stderr = e.stderr.decode() if hasattr(e, 'stderr') else "Timeout installing pytest."
             return {"passed": False, "stdout": "", "stderr": f"Failed to install pytest in sandbox: {stderr}"}

        # 3. Write all the provided files to the sandbox
        for rel_path, content in files_to_write.items():
            abs_path = tmpdir_path / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 4. FIX: Recursively find and install all requirements.txt files
        print("Searching for and installing project dependencies...")
        found_reqs = False
        for root, _, files in os.walk(tmpdir_path):
            if 'requirements.txt' in files:
                requirements_path = Path(root) / 'requirements.txt'
                print(f"  - Installing dependencies from: {requirements_path.relative_to(tmpdir_path)}")
                found_reqs = True
                try:
                    subprocess.run([pip_executable, "install", "-r", str(requirements_path)], check=True, capture_output=True, timeout=300)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    stderr = e.stderr.decode() if hasattr(e, 'stderr') else "Timeout installing requirements."
                    print(f"    - WARNING: Failed to install dependencies from this file. Error: {stderr[:300]}...")
        if not found_reqs:
            print("  - No requirements.txt files found.")
        
        # 5. Execute the test command using the venv's python and setting PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = str(tmpdir_path)
        
        python_executable = str(venv_path / "bin" / "python")
        if sys.platform == "win32":
            python_executable = str(venv_path / "Scripts" / "python.exe")
        
        full_test_command = f"{python_executable} -m {test_command}"

        try:
            process = subprocess.run(
                full_test_command,
                shell=True,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            return { "passed": process.returncode == 0, "stdout": process.stdout, "stderr": process.stderr }
        except subprocess.TimeoutExpired:
            return { "passed": False, "stdout": "", "stderr": "Error: Test execution timed out." }
        except Exception as e:
            return { "passed": False, "stdout": "", "stderr": f"An unexpected error occurred: {e}" }