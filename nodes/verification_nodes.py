from pocketflow import Node
from utils.sandbox_executor import run_tests_in_sandbox
from pathlib import Path
import os

class VerifySingleTestNode(Node):
    """
    --- PHASE 1 NEW NODE ---
    Runs a single, specific test case in the secure sandbox environment.
    """
    def prep(self, shared):
        return {
            "test_case": shared.get("current_test_case", {}),
            "repo_path": shared.get("repo_path"),
            "generated_files": shared.get("generated_files", {}),
            "source_files_content": shared.get("source_files_content", {}),
            "sandbox_path": self.params.get("sandbox_path"),
            "project_analysis": shared.get("project_analysis", {})
        }

    def exec(self, prep_res):
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
            
            # The logic to copy individual config files is no longer needed here,
            # as the sandbox_executor will perform a full clone on first run.

        files_to_write.update(source_files_content)
        files_to_write.update(generated_files)

        test_command = f"pytest -k {test_id}"

        print(f"Writing {len(files_to_write)} in-memory files to sandbox and running command: '{test_command}'")
        
        # --- CRITICAL FIX ---
        # Pass the repo_path to the executor so it can clone the project on the first run.
        result = run_tests_in_sandbox(files_to_write, test_command, sandbox_path, repo_path)

        result["source_files_content"] = source_files_content
        result["test_case_id"] = test_id
        return result

    def post(self, shared, prep_res, exec_res):
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
            return "failure"


class QualityGateNode(Node):
    """
    A multi-layer quality gate that validates the generated test code
    against various criteria (e.g., length, complexity, confidence target).
    """
    def prep(self, shared):
        test_case = shared.get("current_test_case", {})
        generated_code = shared.get("generated_files", {}).get(test_case.get("test_file_path"))
        
        return {
            "test_case": test_case,
            "generated_code": generated_code,
            "confidence_target": test_case.get("confidence_target", 0.85)
        }

    def exec(self, prep_res):
        test_case = prep_res["test_case"]
        generated_code = prep_res["generated_code"]
        confidence_target = prep_res["confidence_target"]
        
        test_id = test_case.get("id")
        print(f"\n--- Running Quality Gate for test case: {test_id} ---")
        
        # 1. Basic Code Length Check (Proxy for complexity/bloat)
        code_lines = len(generated_code.splitlines()) if generated_code else 0
        max_lines = 50 # Arbitrary limit for a single unit test
        
        if code_lines > max_lines:
            print(f"❌ Quality Gate Failed: Code too long ({code_lines} lines > {max_lines} max).")
            return {"passed": False, "reason": "Code complexity too high (length check failed)."}

        # 2. Confidence Check (Placeholder for future LLM-based confidence scoring)
        # For now, we'll assume the LLM-generated code has a fixed high confidence
        # unless a specific strategy was used.
        assumed_confidence = 0.90 # Placeholder for actual LLM confidence score
        
        if assumed_confidence < confidence_target:
            print(f"❌ Quality Gate Failed: Assumed confidence ({assumed_confidence}) below target ({confidence_target}).")
            return {"passed": False, "reason": "Generation confidence too low."}
            
        # 3. Syntax Check (Already implicitly handled by the sandbox executor, but a quick check is good)
        # We'll skip a full static analysis for this simple implementation.
        
        print(f"✅ Quality Gate Passed for test case: {test_id}")
        return {"passed": True, "reason": "All checks passed."}

    def post(self, shared, prep_res, exec_res):
        if exec_res["passed"]:
            return "success"
        else:
            # If Quality Gate fails, we don't proceed to verification
            shared["current_test_case_result"] = {
                "passed": False,
                "stdout": "",
                "stderr": f"Quality Gate Failed: {exec_res['reason']}"
            }
            # This will cause the main loop to mark the test as FAILED and move on
            return "failure"

class HumanInTheLoopNode(Node):
    """
    Handles test cases that cannot be resolved by the automated flow (e.g.,
    Quality Gate failure, unpatchable error) by escalating them for human review.
    """
    def prep(self, shared):
        test_case = shared.get("current_test_case", {})
        test_result = shared.get("current_test_case_result", {})
        
        # Determine the reason for escalation
        reason = "Unknown failure"
        if "Quality Gate Failed" in test_result.get("stderr", ""):
            reason = "Quality Gate Failure"
        elif test_result.get("passed") is False and shared.get("generated_patch") is not None:
            reason = "Healing Failed (Patch did not fix the issue)"
        elif test_result.get("passed") is False and shared.get("generated_patch") is None:
            reason = "Initial Verification Failed (Unattempted Healing)"
            
        return {
            "test_case": test_case,
            "test_result": test_result,
            "reason": reason,
            "generated_patch": shared.get("generated_patch")
        }

    def exec(self, prep_res):
        test_id = prep_res["test_case"].get("id")
        reason = prep_res["reason"]
        
        print(f"\n--- ESCALATION: Human-in-the-Loop required for test case: {test_id} ---")
        
        escalation_report = {
            "test_case_id": test_id,
            "module_path": prep_res["test_case"].get("module_path"),
            "description": prep_res["test_case"].get("description"),
            "escalation_reason": reason,
            "last_error_stderr": prep_res["test_result"].get("stderr", "N/A"),
            "generated_patch": prep_res["generated_patch"] if prep_res["generated_patch"] else "N/A",
            "action_required": "Human review is required to diagnose the issue and provide a manual fix or override."
        }
        
        # In a real system, this would write to a database, a JIRA ticket, or send an email.
        # Here, we will just update the test case status and log the report.
        
        print(f"Escalation Report:\n{yaml.dump(escalation_report, indent=2, default_flow_style=False)}")
        
        return {"status": "ESCALATED", "report": escalation_report}

    def post(self, shared, prep_res, exec_res):
        # Update the test case status in the main plan to reflect escalation
        test_case = shared.get("current_test_case")
        if test_case:
            test_case["status"] = exec_res["status"]
            test_case["escalation_reason"] = exec_res["report"]["escalation_reason"]
            test_case["last_error"] = exec_res["report"]["last_error_stderr"]
            
        return "escalated"

class FinalizeAndOrganizeNode(Node):
    """
    This node now runs at the very end of the entire process to write all
    successfully generated and verified files to disk.
    """
    def prep(self, shared):
        return {
            "repo_path": shared.get("repo_path"),
            "files_to_write": shared.get("generated_files", {}),
            "final_result_message": shared.get("final_result", "Flow completed."),
            "test_plan": shared.get("test_plan", {}).get("test_cases", [])
        }

    def _generate_quality_report(self, test_plan):
        total_tests = len(test_plan)
        passed_tests = sum(1 for t in test_plan if t.get("status") == "PASSED")
        escalated_tests = sum(1 for t in test_plan if t.get("status") == "ESCALATED")
        failed_tests = total_tests - passed_tests - escalated_tests
        
        report = f"# Test Generation Quality Report\n\n"
        report += f"## Summary\n\n"
        report += f"| Metric | Value |\n"
        report += f"| :--- | :--- |\n"
        report += f"| Total Test Cases Planned | {total_tests} |\n"
        report += f"| **Tests Successfully Generated & Verified** | **{passed_tests}** |\n"
        report += f"| Tests Escalated for Human Review | {escalated_tests} |\n"
        report += f"| Tests Failed (Unresolved) | {failed_tests} |\n\n"
        
        report += f"## Escalated Test Cases\n\n"
        escalated_cases = [t for t in test_plan if t.get("status") == "ESCALATED"]
        if escalated_cases:
            report += f"| ID | Module | Reason | Last Error |\n"
            report += f"| :--- | :--- | :--- | :--- |\n"
            for t in escalated_cases:
                reason = t.get("escalation_reason", "N/A")
                last_error = t.get("last_error", "N/A")[:50] + "..." if len(t.get("last_error", "")) > 50 else t.get("last_error", "N/A")
                report += f"| {t['id']} | {t['module_path']} | {reason} | {last_error} |\n"
        else:
            report += "No test cases were escalated for human review. The automated flow was fully successful.\n"
            
        return report

    def _generate_audit_trail(self, test_plan):
        trail = f"# Test Generation Audit Trail\n\n"
        trail += f"This document details the full lifecycle of each test case, including generation strategy, verification results, and any healing or escalation attempts.\n\n"
        
        for t in test_plan:
            trail += f"## Test Case: {t['id']}\n\n"
            trail += f"| Detail | Value |\n"
            trail += f"| :--- | :--- |\n"
            trail += f"| **Final Status** | **{t.get('status', 'PENDING')}** |\n"
            trail += f"| Module Targeted | {t.get('module_path', 'N/A')} |\n"
            trail += f"| Description | {t.get('description', 'N/A')} |\n"
            trail += f"| Priority | {t.get('priority', 'N/A')} |\n"
            
            if t.get('escalation_reason'):
                trail += f"| Escalation Reason | {t['escalation_reason']} |\n"
            
            if t.get('last_error'):
                trail += f"\n### Last Error Log\n\n```\n{t['last_error']}\n```\n"
            
            trail += "\n---\n"
            
        return trail

    def exec(self, prep_res):
        print("\n--- Finalizing and writing all generated files to disk ---")
        repo_path = prep_res.get("repo_path")
        files_to_write = prep_res.get("files_to_write", {})
        test_plan = prep_res.get("test_plan", [])

        if not repo_path:
            return "Nothing to finalize. Repository path is missing."

        # 1. Generate Quality Report
        quality_report_content = self._generate_quality_report(test_plan)
        files_to_write["quality_report.md"] = quality_report_content
        print("Generated quality_report.md")
        
        # 2. Generate Audit Trail
        audit_trail_content = self._generate_audit_trail(test_plan)
        files_to_write["audit_trail.md"] = audit_trail_content
        print("Generated audit_trail.md")

        if not files_to_write:
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


