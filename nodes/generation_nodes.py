import yaml
from pathlib import Path
from pocketflow import AsyncNode, AsyncParallelBatchNode
from utils.async_call_llm import call_llm
from utils.knowledge_graph import query_index
from unidiff import PatchSet
import io
import re


class PlanTestsNode(AsyncNode):
    """
    An intelligent agent that queries the KG to create a high-level,
    strategic test plan for the entire codebase.

    --- PHASE 1 EVOLUTION ---
    This node now generates a detailed, stateful checklist of individual
    test cases that will drive the entire online execution flow.
    """
    async def prep_async(self, shared):
        project_analysis = shared.get("project_analysis", {})
        return project_analysis

    async def exec_async(self, prep_res):
        project_analysis = prep_res
        print("Planning test suite by generating a detailed test case checklist...")
        source_files = project_analysis.get("source_files", [])
        if not source_files:
            raise ValueError("No source files found in project_analysis to create a test plan.")

        prompt = f"""
You are a senior test architect. Based on the following list of source files, create a detailed test plan in YAML format.
For each module, propose a list of specific test cases to cover its functionality (happy paths, edge cases, error conditions).

Your plan must be in YAML format and contain a single top-level key: `test_cases`.
Each item in the `test_cases` list must have the following fields:
- id: A unique, valid Python function name for the test (e.g., "test_user_creation_valid_input").
- module_path: The full path to the source code module that this test case targets.
- status: "PENDING"  # This is the initial state for all generated cases.
- priority: "HIGH", "MEDIUM", or "LOW", based on the perceived importance of the test.
- description: A concise, one-sentence explanation of the test's purpose.

Project Files:
{', '.join(source_files)}

Respond ONLY with the YAML block for the test plan. Do not include any other text or markdown formatting.
Example:
```yaml
test_cases:
  - id: "test_calculate_shipping_cost_normal"
    module_path: "src/shipping_calculator.py"
    status: "PENDING"
    priority: "HIGH"
    description: "Tests shipping calculation for a standard domestic address."
  - id: "test_calculate_shipping_cost_international"
    module_path: "src/shipping_calculator.py"
    status: "PENDING"
    priority: "MEDIUM"
    description: "Tests shipping calculation for an international address with customs."
```
"""
        plan_yaml_str = await call_llm(prompt)
        try:
            # Clean up potential markdown formatting from the LLM response
            if "```yaml" in plan_yaml_str:
                plan_yaml_str = plan_yaml_str.split("```yaml")[1].split("```")[0].strip()
            elif plan_yaml_str.strip().startswith("```"):
                plan_yaml_str = plan_yaml_str.strip()[3:-3].strip()
            
            plan = yaml.safe_load(plan_yaml_str)
            if not isinstance(plan, dict) or "test_cases" not in plan:
                raise ValueError("Parsed YAML is missing the required 'test_cases' key.")
        except (yaml.YAMLError, IndexError, ValueError) as e:
            print(f"Error parsing test plan YAML from LLM response: {e}")
            print(f"--- Raw LLM Response ---\n{plan_yaml_str}\n--------------------")
            raise ValueError("Failed to parse a valid test plan from LLM response.")
        return plan

    async def post_async(self, shared, prep_res, exec_res):
        shared["test_plan"] = exec_res
        tasks = len(exec_res.get("test_cases", []))
        print(f"Test plan created with {tasks} individual test cases.")


class GenerateSingleTestNode(AsyncNode):
    """
    --- PHASE 1 NEW NODE ---
    Generates the code for a single test case from the checklist.
    It uses RAG to provide relevant context to the LLM.
    """
    async def prep_async(self, shared):
        return {
            "test_case": shared.get("current_test_case"),
            "project_analysis": shared.get("project_analysis", {}),
            "repo_path": self.params.get("repo_path")
        }

    async def exec_async(self, prep_res):
        test_case = prep_res.get("test_case")
        project_analysis = prep_res.get("project_analysis")
        repo_path = prep_res.get("repo_path")

        if not test_case:
            return {"status": "SKIPPED", "reason": "No current_test_case in shared store."}

        module_path = test_case.get("module_path")
        print(f"Generating code for test case: {test_case['id']}")

        # RAG step: Get context for the specific module
        context_summaries = await query_index(f"all function and class summaries for file {module_path}", top_k=10)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}" for s in context_summaries]) if context_summaries else "No specific context found."

        framework = project_analysis.get("test_framework", "pytest")

        prompt = f"""
You are an expert Python test engineer. Your task is to write a single, complete, runnable test function for the following test case using the {framework} framework.

Test Case Details:
- Function to write: def {test_case['id']}(self): (if in a class) or def {test_case['id']}(): (if standalone)
- Module to test: {module_path}
- Description: {test_case['description']}

Relevant Context from Knowledge Graph:
{context_str}

IMPORTANT INSTRUCTIONS:
1. Generate ONLY the code for the single test function {test_case['id']}.
2. Do NOT generate the full file, class structure, or other test functions.
3. Ensure necessary imports are included within the function if they are not standard libraries, or assume they exist at the top of the file.
4. The generated code must be a complete, syntactically correct Python function.
5. Do NOT include explanations, comments, or markdown formatting. Start with def and end with the last line of the function's code.
"""
        test_code = await call_llm(prompt)
        
        # Clean the response to get only the code
        if "```python" in test_code:
            test_code = test_code.split("```python")[1].split("```")[0].strip()
        elif test_code.strip().startswith("```"):
            test_code = test_code.strip()[3:-3].strip()

        # Determine the destination test file path
        try:
            # Use .stem to get the filename without extension
            relative_module_path = Path(module_path).relative_to(repo_path)
            test_filename = f"test_{relative_module_path.stem}.py"
            test_file_path = str(Path("tests") / relative_module_path.parent / test_filename)
        except ValueError:
            test_file_path = f"tests/test_{Path(module_path).stem}.py"

        return {"test_case_id": test_case["id"], "test_file_path": test_file_path, "code": test_code}

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res.get("status") == "SKIPPED":
            print(f"Skipped test generation: {exec_res.get('reason')}")
            return
        
        test_file_path = exec_res["test_file_path"]
        new_code = exec_res["code"]

        if "generated_files" not in shared:
            shared["generated_files"] = {}

        # Append the new test function to the existing file in memory, or create it
        if test_file_path in shared["generated_files"]:
            shared["generated_files"][test_file_path] += f"\n\n{new_code}"
        else:
            # A basic template for a new test file
            shared["generated_files"][test_file_path] = f"# Test file for {prep_res['test_case']['module_path']}\nimport pytest\n\n{new_code}"

        print(f"Appended test case {exec_res['test_case_id']} to in-memory file {test_file_path}")


# ==================================================================
# The nodes below are now considered LEGACY and are not used by the
# new Phase 1 orchestration logic. They will be removed or replaced
# in Phase 2 (Healing).
# ==================================================================

class GenerateUnitTestsNode(AsyncParallelBatchNode):
    """
    [LEGACY] Generates unit tests for each module defined in the test plan.
    """
    concurrency = 5
    
    async def prep_async(self, shared): 
        return []
    
    async def exec_async(self, item): 
        return {}
    
    async def post_async(self, shared, prep_res, exec_res_list): 
        pass


class HealNode(AsyncNode):
    """
    [LEGACY] An autonomous agent that attempts to fix failing tests.
    """
    def _extract_focused_error(self, stdout: str, stderr: str) -> str: 
        return ""
    
    async def prep_async(self, shared): 
        return None
    
    async def exec_async(self, prep_res): 
        return {}
    
    async def post_async(self, shared, prep_res, exec_res): 
        return "unpatchable"