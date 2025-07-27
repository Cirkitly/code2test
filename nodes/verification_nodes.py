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
        return {
            "project_analysis": shared.get("project_analysis", {}),
            "repo_path": shared.get("repo_path"),
            "generated_files": shared.get("generated_files", {}),
            "source_files_content": shared.get("source_files_content", {})
        }

    def exec(self, prep_res):
        print("\n--- Verifying test suite in sandboxed environment ---")
        
        repo_path = prep_res.get("repo_path")
        generated_files = prep_res.get("generated_files", {})
        source_files_content = prep_res.get("source_files_content", {})
        
        # This is the master dictionary of all files to be written to the sandbox.
        files_to_write = {}

        # 1. Populate source files from disk IF they haven't been loaded before.
        # This happens on the first run. On subsequent runs (after a patch),
        # we use the (potentially modified) in-memory versions.
        if not source_files_content:
            print("First run: Loading source files from disk into memory...")
            project_analysis = prep_res.get("project_analysis", {})
            source_paths = project_analysis.get("source_files", [])
            for path_str in source_paths:
                try:
                    # Create a path relative to the repo root, which is what the AI will see.
                    relative_path = str(Path(path_str).relative_to(repo_path))
                    with open(path_str, 'r', encoding='utf-8') as f:
                        source_files_content[relative_path] = f.read()
                except (FileNotFoundError, ValueError) as e:
                    print(f"Warning: Could not process source file {path_str}: {e}")
        else:
            print("Subsequent run: Using in-memory source files (may include patches).")

        # 2. Add all source files (original or patched) to the sandbox files.
        files_to_write.update(source_files_content)

        # 3. Add all generated test files (original or patched) to the sandbox files.
        files_to_write.update(generated_files)

        if not generated_files:
            print("Warning: No test files were generated to verify. Marking as successful.")
            return {"passed": True, "stdout": "No tests to run.", "stderr": "", "source_files_content": {}}

        print(f"Writing {len(files_to_write)} files to sandbox for testing...")
        test_command = "pytest"
        
        result = run_tests_in_sandbox(files_to_write, test_command)
        
        # Pass the state of source files back to be updated in the shared store.
        result["source_files_content"] = source_files_content
        return result

    def post(self, shared, prep_res, exec_res):
        # IMPORTANT: Persist the state of the source files for the next loop iteration.
        shared["source_files_content"] = exec_res["source_files_content"]
        
        if exec_res["passed"]:
            print("✅ Verification successful! All tests passed.")
            shared["final_result"] = exec_res["stdout"]
            # All files (source and test) are now in a good state.
            # We update `generated_files` to include all files for final writing.
            shared["generated_files"].update(shared["source_files_content"])
            return "success"
        else:
            print("❌ Verification failed. Capturing context for the healing agent.")
            
            # --- ADDED DIAGNOSTIC LOGGING ---
            # Print the raw output from the sandbox to see what's really happening.
            print("\n--- SANDBOX STDOUT ---")
            print(exec_res.get("stdout", "No STDOUT captured."))
            print("--- SANDBOX STDERR ---")
            print(exec_res.get("stderr", "No STDERR captured."))
            print("----------------------\n")
            
            shared["failure_context"] = exec_res
            return "failure"

class FinalizeAndOrganizeNode(Node):
    """
    Once tests are verified, this node writes the final,
    working test files (and any patched source files) to the user's actual
    repository filesystem.
    """
    def prep(self, shared):
        # Final set of files to write includes tests and any patched source files.
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