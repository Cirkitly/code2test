import os
from pathlib import Path

def discover_code_files(repo_path: str, extensions=('.py', '.c', '.rs', '.js')) -> list[str]:
    """Recursively finds all code files with given extensions."""
    code_files = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(extensions):
                code_files.append(str(Path(root) / file))
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
    with open("temp_project/src/main.py", "w") as f:
        f.write("def hello():\n    print('hello')\n")
    with open("temp_project/src/utils.py", "w") as f:
        f.write("def utility_func():\n    return True\n")

    files = discover_code_files("./temp_project")
    print("Discovered files:", files)

    units = extract_code_units("./temp_project/src/main.py")
    print("Extracted units from main.py:", units)