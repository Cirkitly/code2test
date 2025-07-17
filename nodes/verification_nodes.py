from pocketflow import Node
from utils.sandbox_executor import run_tests_in_sandbox
from pathlib import Path

class VerifyTestsNode(Node):
    """
    Runs the full suite of generated tests in a secure, isolated sandbox
    environment and checks the results.
    """
    def prep(self, shared):
        # FIX: Read all necessary data from the shared store.
        return {
            "project_analysis": shared.get("project_analysis", {}),
            "repo_path": shared.get("repo_path"),
            "generated_files": shared.get("generated_files", {})
        }

    def exec(self, prep_res):
        print("Verifying generated test suite in a sandboxed environment...")
        
        project_analysis = prep_res.get("project_analysis", {})
        repo_path = prep_res.get("repo_path")
        generated_files = prep_res.get("generated_files", {})
        
        if not generated_files:
            print("Warning: No test files were generated to verify. Marking as successful.")
            return {"passed": True, "stdout": "No tests to run.", "stderr": ""}

        files_to_write = {}
        files_to_write.update(generated_files)
        
        source_paths = project_analysis.get("source_files", [])
        for path_str in source_paths:
            try:
                relative_path = Path(path_str).relative_to(repo_path)
                with open(path_str, 'r', encoding='utf-8') as f:
                    files_to_write[str(relative_path)] = f.read()
            except (FileNotFoundError, ValueError) as e:
                print(f"Warning: Could not process source file {path_str}: {e}")

        test_command = "pytest"
        
        result = run_tests_in_sandbox(files_to_write, test_command)
        return result

    def post(self, shared, prep_res, exec_res):
        if exec_res["passed"]:
            print("✅ Verification successful! All tests passed.")
            shared["final_result"] = exec_res["stdout"]
            return "success"
        else:
            print("❌ Verification failed. Capturing context for the healing agent.")
            shared["failure_context"] = exec_res
            return "failure"

class FinalizeAndOrganizeNode(Node):
    """
    (Placeholder) Once tests are verified, this node would write the final,
    working test files to the user's actual repository filesystem.
    """
    def prep(self, shared):
        # FIX: Read from shared store.
        return {
            "repo_path": shared.get("repo_path"),
            "generated_files": shared.get("generated_files", {})
        }

    def exec(self, prep_res):
        print("Finalizing and organizing the verified test suite...")
        
        repo_path = prep_res.get("repo_path")
        generated_files = prep_res.get("generated_files", {})

        if not repo_path or not generated_files:
            return "Nothing to finalize."

        for relative_path_str, content in generated_files.items():
            destination_path = Path(repo_path) / relative_path_str
            
            try:
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                with open(destination_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  - Wrote file to: {destination_path}")
            except Exception as e:
                print(f"  - FAILED to write file to {destination_path}: {e}")
        
        return "Test suite generated and verified successfully. Files written to disk."

    def post(self, shared, prep_res, exec_res):
        shared["final_result"] = exec_res
        print(f"\n🎉 {exec_res}")