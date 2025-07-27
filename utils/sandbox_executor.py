import subprocess
import tempfile
import os
import sys
from pathlib import Path

def run_tests_in_sandbox(files_to_write: dict, test_command: str, sandbox_path: str) -> dict:
    """
    Uses a persistent sandbox directory, sets up the environment on the first run,
    installs all project dependencies, and then runs tests.
    """
    tmpdir_path = Path(sandbox_path)
    venv_path = tmpdir_path / "venv"
    
    # Determine executables first
    pip_executable = str(venv_path / "bin" / "pip")
    python_executable = str(venv_path / "bin" / "python")
    if sys.platform == "win32":
        pip_executable = str(venv_path / "Scripts" / "pip.exe")
        python_executable = str(venv_path / "Scripts" / "python.exe")

    # Perform expensive, one-time setup if the venv doesn't exist
    if not venv_path.exists():
        print("Sandbox venv not found. Performing first-time setup...")
        try:
            # 1. Create venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True, capture_output=True, timeout=60)
            
            # 2. Upgrade pip and install pytest
            print("  - Installing/upgrading pip and pytest...")
            subprocess.run([pip_executable, "install", "--upgrade", "pip"], check=True, capture_output=True, timeout=60)
            subprocess.run([pip_executable, "install", "pytest"], check=True, capture_output=True, timeout=120)

            # 3. Write all project/test files to the sandbox BEFORE installing
            for rel_path, content in files_to_write.items():
                abs_path = tmpdir_path / rel_path
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # 4. Install all found requirements.txt files
            print("  - Searching for and installing project dependencies from requirements.txt...")
            for root, _, files in os.walk(tmpdir_path):
                if 'requirements.txt' in files:
                    req_path = Path(root) / 'requirements.txt'
                    print(f"    - Installing from: {req_path.relative_to(tmpdir_path)}")
                    subprocess.run([pip_executable, "install", "-r", str(req_path)], capture_output=True, timeout=300)

            # 5. FINAL UPGRADE: Install the project itself in editable mode if setup.py exists
            if (tmpdir_path / 'setup.py').exists():
                print("  - Found setup.py, installing project in editable mode...")
                subprocess.run([pip_executable, "install", "-e", "."], cwd=tmpdir_path, capture_output=True, timeout=300)
            
            print("  - First-time setup complete.")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            stderr = e.stderr.decode() if hasattr(e, 'stderr') else "Operation timed out."
            return {"passed": False, "stdout": "", "stderr": f"Failed during sandbox setup: {stderr}"}
    else:
        print("Sandbox venv found. Re-writing files for this run...")
        # On subsequent runs, just write the (potentially patched) files
        for rel_path, content in files_to_write.items():
            abs_path = tmpdir_path / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)

    # 6. Execute the test command
    env = os.environ.copy()
    env['PYTHONPATH'] = str(tmpdir_path) # Ensure root is on path
    full_test_command = f"{python_executable} -m {test_command}"

    try:
        process = subprocess.run(
            full_test_command, shell=True, cwd=tmpdir_path,
            capture_output=True, text=True, timeout=300, env=env
        )
        return {"passed": process.returncode == 0, "stdout": process.stdout, "stderr": process.stderr}
    except subprocess.TimeoutExpired:
        return {"passed": False, "stdout": "", "stderr": "Error: Test execution timed out."}
    except Exception as e:
        return {"passed": False, "stdout": "", "stderr": f"An unexpected error occurred: {e}"}