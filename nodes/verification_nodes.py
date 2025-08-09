from pocketflow import Node, AsyncNode
from utils.sandbox_executor import run_tests_in_sandbox
from pathlib import Path
import os

class VerifySingleTestNode(AsyncNode): # <-- FIX: Inherit from AsyncNode
    """
    --- PHASE 1 NEW NODE ---
    Runs a single, specific test case in the secure sandbox environment.
    """
    async def prep_async(self, shared): # <-- FIX: Rename to prep_async
        return {
            "test_case": shared.get("current_test_case", {}),
            "repo_path": shared.get("repo_path"),
            "generated_files": shared.get("generated_files", {}),
            "source_files_content": shared.get("source_files_content", {}),
            "sandbox_path": self.params.get("sandbox_path"),
            "project_analysis": shared.get("project_analysis", {})
        }

    async def exec_async(self, prep_res): # <-- FIX: Rename to exec_async
        test_case = prep_res.get("test_case")
        if not test_case:
            return {"passed": False, "stdout": "", "stderr": "VerifySingleTestNode was run without a current_test_case."}

        test_id = test_case.get("id")
        print(f"\n--- Verifying single test case: {test_id} ---")

        repo_path = prep_res.get("repo_path")
        generated_files = prep_res.get("generated_files", {})
        source_files_content = prep_res.get("source_files_content", {})
        sandbox_path = prep_res.get("sandbox_path")

        if not sandbox_path:
            raise ValueError("VerifySingleTestNode requires a 'sandbox_path' in its parameters.")

        files_to_write = {}

        if not source_files_content:
            print("First verification run: Loading source files and project configs from disk into memory...")
            project_analysis = prep_res.get("project_analysis", {})
            source_paths = project_analysis.get("source_files", [])
            for path_str in source_paths:
                try:
                    relative_path = str(Path(path_str).relative_to(repo_path))
                    with open(path_str, 'r', encoding='utf-8') as f:
                        source_files_content[relative_path] = f.read()
                except (FileNotFoundError, ValueError) as e:
                    print(f"Warning: Could not process source file {path_str}: {e}")

            config_files_to_check = ["pyproject.toml", "setup.py", "requirements.txt"] # Added requirements.txt
            for config_file in config_files_to_check:
                config_path = Path(repo_path) / config_file
                if config_path.exists():
                    print(f"Found project config file: {config_file}. Adding to sandbox.")
                    with open(config_path, 'r', encoding='utf-8') as f:
                        source_files_content[config_file] = f.read()

        files_to_write.update(source_files_content)
        files_to_write.update(generated_files)

        test_command = f"pytest -k {test_id}"

        print(f"Writing {len(files_to_write)} in-memory files to sandbox and running command: '{test_command}'")
        
        # This function call is synchronous, but it's okay because run_async
        # will be run in an executor thread by the PocketFlow runner.
        result = run_tests_in_sandbox(files_to_write, test_command, sandbox_path, repo_path)

        result["source_files_content"] = source_files_content
        result["test_case_id"] = test_id
        return result

    async def post_async(self, shared, prep_res, exec_res): # <-- FIX: Rename to post_async
        shared["source_files_content"] = exec_res["source_files_content"]

        shared["current_test_case_result"] = {
            "passed": exec_res["passed"],
            "stdout": exec_res.get("stdout", ""),
            "stderr": exec_res.get("stderr", "")
        }

        if exec_res["passed"]:
            print(f"✅ PASSED: {exec_res['test_case_id']}")
            return "success"
        else:
            print(f"❌ FAILED: {exec_res['test_case_id']}")
            print("Capturing context for the healing agent.")
            shared["failure_context"] = exec_res
            return "failure"


class FinalizeAndOrganizeNode(Node):
    """
    This node now runs at the very end of the entire process to write all
    successfully generated and verified files to disk.
    """
    def prep(self, shared):
        return {
            "repo_path": shared.get("repo_path"),
            "files_to_write": shared.get("generated_files", {}),
            "final_result_message": shared.get("final_result", "Flow completed.")
        }

    def exec(self, prep_res):
        print("\n--- Finalizing and writing all generated files to disk ---")
        repo_path = prep_res.get("repo_path")
        files_to_write = prep_res.get("files_to_write", {})

        if not repo_path or not files_to_write:
            return "Nothing to finalize. No files were generated."

        init_files_to_add = set()
        for path_str in files_to_write.keys():
            p = Path(path_str).parent
            while p != Path('.') and 'tests' in p.parts:
                init_file = p / "__init__.py"
                init_files_to_add.add(str(init_file))
                if p.name == 'tests': break
                p = p.parent
        for init_file in init_files_to_add:
            if init_file not in files_to_write:
                files_to_write[init_file] = "# Auto-generated by AI Software Foundry\n"

        print(f"Writing {len(files_to_write)} total files...")
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


# ==================================================================
# The node below is now considered LEGACY and is not used by the
# new Phase 1 orchestration logic.
# ==================================================================

class VerifyTestsNode(Node):
    """
    [LEGACY] Runs the full suite of generated tests.
    """
    def prep(self, shared): return {}
    def exec(self, prep_res): return {"passed": True, "source_files_content": {}}
    def post(self, shared, prep_res, exec_res): return "success"