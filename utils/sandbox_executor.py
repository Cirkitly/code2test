import subprocess
import tempfile
import os
import sys
import shutil
from pathlib import Path

def run_tests_in_sandbox(files_to_write: dict, test_command: str, sandbox_path: str, repo_path: str) -> dict:
    """
    Uses a persistent sandbox directory. On first run, it creates a venv,
    clones the entire source repository into it, installs dependencies,
    and then runs tests. On subsequent runs, it just updates files.
    """
    tmpdir_path = Path(sandbox_path)
    venv_path = tmpdir_path / "venv"

    pip_executable = str(venv_path / "bin" / "pip")
    python_executable = str(venv_path / "bin" / "python")
    if sys.platform == "win32":
        pip_executable = str(venv_path / "Scripts" / "pip.exe")
        python_executable = str(venv_path / "Scripts" / "python.exe")

    if not venv_path.exists():
        print("Sandbox venv not found. Performing first-time setup...")
        try:
            # 1. --- CRITICAL FIX: Clone the entire repository into the sandbox ---
            # This ensures all necessary files (README.md, etc.) are present for the build.
            print(f"  - Cloning repository from {repo_path} to {sandbox_path}...")
            ignore_patterns = shutil.ignore_patterns('.git', '__pycache__', 'venv', '.venv', '*_cache')
            shutil.copytree(repo_path, sandbox_path, dirs_exist_ok=True, ignore=ignore_patterns)

            # 2. Create virtual environment
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True, capture_output=True, text=True, timeout=60)

            # 3. Upgrade pip and install pytest
            print("  - Installing/upgrading pip and pytest...")
            subprocess.run([pip_executable, "install", "--upgrade", "pip"], check=True, capture_output=True, text=True, timeout=60)
            subprocess.run([pip_executable, "install", "pytest"], check=True, capture_output=True, text=True, timeout=120)

            # 4. Install the project itself in editable mode
            is_installable = (tmpdir_path / 'pyproject.toml').exists() or (tmpdir_path / 'setup.py').exists()
            if is_installable:
                print("  - Found pyproject.toml or setup.py, installing project in editable mode...")
                install_result = subprocess.run(
                    [pip_executable, "install", "-e", "."],
                    cwd=tmpdir_path, capture_output=True, text=True, timeout=300
                )
                if install_result.returncode != 0:
                    print("    - WARNING: Project installation failed. Tests may fail due to missing dependencies.")
                    print(f"    - PIP STDOUT: {install_result.stdout}")
                    print(f"    - PIP STDERR: {install_result.stderr}")
            else:
                 print("  - No pyproject.toml or setup.py found. Skipping project installation.")

            print("  - First-time setup complete.")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            stdout = e.stdout if hasattr(e, 'stdout') else "No STDOUT."
            stderr = e.stderr if hasattr(e, 'stderr') else "Operation timed out."
            return {"passed": False, "stdout": stdout, "stderr": f"Failed during sandbox setup: {stderr}"}
        except Exception as e:
            return {"passed": False, "stdout": "", "stderr": f"An unexpected error occurred during sandbox setup: {e}"}

    # On every run (including first), write the in-memory files (source + generated tests)
    # to the sandbox. This overwrites the cloned files with any potential patches
    # and adds the newly generated test files.
    for rel_path, content in files_to_write.items():
        abs_path = tmpdir_path / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # Execute the test command
    env = os.environ.copy()
    env['PYTHONPATH'] = str(tmpdir_path)
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