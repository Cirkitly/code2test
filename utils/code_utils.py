import os
from pathlib import Path

def discover_code_files(repo_path: str, extensions=('.py',), exclude_patterns=('test_', '_test.py', 'tests/')) -> list[str]:
    """
    Recursively finds all code files with given extensions, excluding common
    test files and test directories.
    
    --- FIX: We now INCLUDE __init__.py files in discovery so they are copied
    to the sandbox, preserving the project's package structure. ---
    """
    code_files = []
    repo_path_obj = Path(repo_path)

    for root, dirs, files in os.walk(repo_path):
        # Exclude common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('__') and 'site-packages' not in d and 'venv' not in d and 'tests' not in d]

        for file in files:
            file_path_str = str(Path(root) / file)
            # Check file extensions
            if not file.endswith(extensions):
                continue
            
            # Check exclude patterns
            if any(p in file_path_str for p in exclude_patterns):
                continue
            
            code_files.append(file_path_str)
            
    return code_files

def extract_code_units(file_path: str) -> list[dict]:
    """
    A simplified function to extract "units" (e.g., functions) from a file.
    In a real system, this would use a proper AST parser for each language.
    For this example, we'll treat the entire file as a single unit.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Simple strategy: one file = one unit.
        return [{
            "unit_name": Path(file_path).name,
            "file_path": file_path,
            "code": content
        }]
    except Exception as e:
        print(f"Could not read or parse {file_path}: {e}")
        return []

if __name__ == "__main__":
    # Create a dummy project structure for testing
    os.makedirs("temp_project/src", exist_ok=True)
    os.makedirs("temp_project/tests", exist_ok=True)
    with open("temp_project/src/main.py", "w") as f:
        f.write("def hello():\n    print('hello')\n")
    with open("temp_project/src/utils.py", "w") as f:
        f.write("def utility_func():\n    return True\n")
    with open("temp_project/src/__init__.py", "w") as f:
        f.write("")
    with open("temp_project/tests/test_utils.py", "w") as f:
        f.write("from src.utils import utility_func\n")

    files = discover_code_files("./temp_project")
    print("Discovered files (should now include __init__.py):", files)

    units = extract_code_units("./temp_project/src/main.py")
    print("Extracted units from main.py:", units)