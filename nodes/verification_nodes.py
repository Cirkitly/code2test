from pocketflow import Node
from utils.sandbox_executor import run_tests_in_sandbox
from pathlib import Path

class VerifyTestsNode(Node):
    """
    Runs the full suite of generated tests in a secure, isolated sandbox
    environment and checks the results. This node also manages the in-memory
    state of all source and test files for the healing loop.
    """
    def prep(self, shared):
        # --- CHANGE: GET THE PERSISTENT SANDBOX PATH ---
        return {
            "project_analysis": shared.get("project_analysis", {}),
            "repo_path": shared.get("repo_path"),
            "generated_files": shared.get("generated_files", {}),
            "source_files_content": shared.get("source_files_content", {}),
            "sandbox_path": self.params.get("sandbox_path") # Get from params
        }

    def exec(self, prep_res):
        print("\n--- Verifying test suite in sandboxed environment ---")
        
        repo_path = prep_res.get("repo_path")
        generated_files = prep_res.get("generated_files", {})
        source_files_content = prep_res.get("source_files_content", {})
        sandbox_path = prep_res.get("sandbox_path")

        if not sandbox_path:
            raise ValueError("VerifyTestsNode requires a 'sandbox_path' in its parameters.")

        files_to_write = {}

        if not source_files_content:
            print("First verification run: Loading source files from disk into memory...")
            project_analysis = prep_res.get("project_analysis", {})
            source_paths = project_analysis.get("source_files", [])
            for path_str in source_paths:
                try:
                    relative_path = str(Path(path_str).relative_to(repo_path))
                    with open(path_str, 'r', encoding='utf-8') as f:
                        source_files_content[relative_path] = f.read()
                except (FileNotFoundError, ValueError) as e:
                    print(f"Warning: Could not process source file {path_str}: {e}")
        else:
            print("Subsequent verification run: Using in-memory source files (may include patches).")

        files_to_write.update(source_files_content)
        files_to_write.update(generated_files)

        if not generated_files:
            print("Warning: No test files were generated to verify. Marking as successful.")
            return {"passed": True, "stdout": "No tests to run.", "stderr": "", "source_files_content": {}}

        print(f"Writing {len(files_to_write)} files to sandbox for testing...")
        test_command = "pytest"
        
        # --- CHANGE: PASS THE SANDBOX PATH TO THE EXECUTOR ---
        result = run_tests_in_sandbox(files_to_write, test_command, sandbox_path)
        
        result["source_files_content"] = source_files_content
        return result

    def post(self, shared, prep_res, exec_res):
        shared["source_files_content"] = exec_res["source_files_content"]
        
        if exec_res["passed"]:
            print("✅ Verification successful! All tests passed.")
            shared["final_result"] = exec_res["stdout"]
            shared["generated_files"].update(shared["source_files_content"])
            return "success"
        else:
            print("❌ Verification failed. Capturing context for the healing agent.")
            print("\n--- SANDBOX STDOUT ---")
            print(exec_res.get("stdout", "No STDOUT captured."))
            print("--- SANDBOX STDERR ---")
            print(exec_res.get("stderr", "No STDERR captured."))
            print("----------------------\n")
            
            shared["failure_context"] = exec_res
            return "failure"

class FinalizeAndOrganizeNode(Node):
    # ... (No changes in this class)
    def prep(self, shared):
        return {
            "repo_path": shared.get("repo_path"),
            "files_to_write": shared.get("generated_files", {}),
            "final_result_message": shared.get("final_result", "Flow completed without a final result message.")
        }
    def exec(self, prep_res):
        print("\n--- Finalizing and organizing the project files ---")
        repo_path = prep_res.get("repo_path")
        files_to_write = prep_res.get("files_to_write", {})
        if not repo_path or not files_to_write:
            return "Nothing to finalize."
        for relative_path_str, content in files_to_write.items():
            destination_path = Path(repo_path) / relative_path_str
            try:
                print(f"  - Writing file to: {destination_path}")
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                with open(destination_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"  - FAILED to write file to {destination_path}: {e}")
        return prep_res.get("final_result_message")
    def post(self, shared, prep_res, exec_res):
        shared["final_result"] = exec_res
        print(f"\n🎉 Flow Complete. Final Status:\n{exec_res}")