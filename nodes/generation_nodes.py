import yaml
from pathlib import Path
from pocketflow import AsyncNode, AsyncParallelBatchNode
from utils.async_call_llm import call_llm
from utils.knowledge_graph import query_index
from unidiff import PatchSet
import io
import re


class MultiToolRouterNode(AsyncNode):
    """
    Selects the optimal test generation strategy (e.g., prompt, toolchain)
    based on the current test case context.
    
    For now, this will simply select a prompt template for the LLM.
    In the future, it will select a full toolchain.
    """
    async def prep_async(self, shared):
        test_case = shared.get("current_test_case")
        project_analysis = shared.get("project_analysis", {})
        
        if not test_case:
            return None
            
        # For a simple implementation, we'll use the priority to select a strategy
        priority = test_case.get("priority", "MEDIUM")
        
        # RAG step: Get context for the specific module
        module_path = test_case.get("module_path")
        context_summaries = await query_index(f"all function and class summaries for file {module_path}", top_k=10)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}" for s in context_summaries]) if context_summaries else "No specific context found."
        
        framework = project_analysis.get("test_framework", "pytest")
        
        # Define different strategies based on priority
        if priority == "HIGH":
            strategy = {
                "name": "High-Priority Strategy (Detailed)",
                "prompt_modifier": "Focus heavily on edge cases, security, and performance. Use property-based testing principles where applicable.",
                "confidence_target": 0.95
            }
        elif priority == "LOW":
            strategy = {
                "name": "Low-Priority Strategy (Basic)",
                "prompt_modifier": "Focus only on the main happy path and basic functionality.",
                "confidence_target": 0.70
            }
        else: # MEDIUM
            strategy = {
                "name": "Medium-Priority Strategy (Standard)",
                "prompt_modifier": "Focus on happy path, one edge case, and one error condition.",
                "confidence_target": 0.85
            }
            
        return {
            "test_case": test_case,
            "context_str": context_str,
            "framework": framework,
            "strategy": strategy
        }

    async def exec_async(self, prep_res):
        if prep_res is None:
            return {"status": "SKIPPED", "reason": "No current_test_case in shared store."}
            
        print(f"Selected strategy: {prep_res['strategy']['name']}")
        return prep_res

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res.get("status") == "SKIPPED":
            return
            
        # Pass the selected strategy and context to the next node (GenerateSingleTestNode)
        shared["generation_context"] = {
            "context_str": exec_res["context_str"],
            "framework": exec_res["framework"],
            "strategy": exec_res["strategy"]
        }
        shared["current_test_case"]["confidence_target"] = exec_res["strategy"]["confidence_target"]

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
    "    async def prep_async(self, shared):
        return {
            "test_case": shared.get("current_test_case"),
            "repo_path": self.params.get("repo_path")
        }

    async def exec_async(self, prep_res):
        test_case = prep_res.get("test_case")
        repo_path = prep_res.get("repo_path")

        if not test_case:
            return {"status": "SKIPPED", "reason": "No current_test_case in shared store."}

        module_path = test_case.get("module_path")
        print(f"Generating code for test case: {test_case['id']}")
        strategy = generation_context.get("strategy", {})
        context_str = generation_context.get("context_str", "No specific context found.")
        framework = generation_context.get("framework", "pytest")
        prompt_modifier = strategy.get("prompt_modifier", "")

        prompt = f"""
You are an expert Python test engineer. Your task is to write a single, complete, runnable test function for the following test case using the {framework} framework.

Test Case Details:
- Function to write: def {test_case['id']}(self): (if in a class) or def {test_case['id']}(): (if standalone)
- Module to test: {module_path}
- Description: {test_case['description']}

Relevant Context from Knowledge Graph:
{context_str}

Generation Strategy: {strategy.get("name", "Standard")}
Strategy Modifier: {prompt_modifier}

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





class LearningEngineNode(AsyncNode):
    """
    The Continuous Learning Engine that updates the strategy based on the outcome
    of the test case execution (success, failure, healing success, escalation).
    
    For now, this is a placeholder for a more complex learning mechanism.
    """
    async def prep_async(self, shared):
        test_case = shared.get("current_test_case")
        test_result = shared.get("current_test_case_result")
        
        if not test_case or not test_result:
            return None
            
        # Extract relevant data for learning
        learning_data = {
            "test_id": test_case.get("id"),
            "final_status": test_case.get("status"),
            "initial_generation_strategy": shared.get("generation_context", {}).get("strategy", {}).get("name"),
            "initial_generation_confidence": shared.get("generation_context", {}).get("strategy", {}).get("confidence_target"),
            "test_passed": test_result.get("passed"),
            "healing_attempted": shared.get("generated_patch") is not None,
            "escalated": test_case.get("status") == "ESCALATED",
            "error_category": test_case.get("escalation_reason") # Re-using escalation reason for error categorization
        }
        
        return learning_data

    async def exec_async(self, prep_res):
        if prep_res is None:
            return {"status": "SKIPPED", "reason": "No test case data for learning."}
            
        print(f"\n--- LEARNING ENGINE: Processing outcome for {prep_res['test_id']} ---")
        
        # Placeholder for complex learning logic (e.g., updating weights, refining RAG query, adjusting confidence)
        # For this implementation, we just log the outcome and simulate a strategy update.
        
        if prep_res["test_passed"]:
            print(f"Outcome: SUCCESS. Strategy '{prep_res['initial_generation_strategy']}' was effective.")
            # In a real system: reinforce the strategy
        elif prep_res["escalated"]:
            print(f"Outcome: ESCALATED. Strategy '{prep_res['initial_generation_strategy']}' failed to resolve issue: {prep_res['error_category']}.")
            # In a real system: penalize the strategy, or refine the planning for this type of module
        elif prep_res["healing_attempted"]:
            print(f"Outcome: HEALING FAILED. Patch did not fix the issue.")
            # In a real system: refine the healing prompt/logic
        else:
            print(f"Outcome: INITIAL FAILURE. Strategy '{prep_res['initial_generation_strategy']}' failed immediately.")
            # In a real system: penalize the strategy
            
        # Simulate a strategy update for the next run (e.g., update a persistent config file)
        # For now, this is a no-op, but the structure is in place.
        
        return {"status": "LEARNING_COMPLETE"}

    async def post_async(self, shared, prep_res, exec_res):
        print(f"Learning Engine finished with status: {exec_res['status']}")
        return "success"

class HealNode(AsyncNode):
    """
    An autonomous agent that attempts to fix failing tests by generating a patch.
    """
    
    async def prep_async(self, shared):
        test_case = shared.get("current_test_case")
        test_result = shared.get("current_test_case_result")
        project_analysis = shared.get("project_analysis", {})
        
        if not test_case or not test_result or test_result.get("passed"):
            return None # Skip if no failed test case is present

        # Get the source file content that needs fixing
        module_path = test_case.get("module_path")
        repo_path = self.params.get("repo_path")
        
        # Read the actual source file content from disk
        try:
            full_path = Path(repo_path) / module_path
            with open(full_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"Error: Source file not found at {full_path}. Cannot heal.")
            return None
        
        return {
            "test_case": test_case,
            "test_result": test_result,
            "source_code": source_code,
            "module_path": module_path,
            "project_analysis": project_analysis
        }

    async def exec_async(self, prep_res):
        if prep_res is None:
            return {"status": "SKIPPED", "reason": "No failed test case to heal."}
            
        test_case = prep_res["test_case"]
        test_result = prep_res["test_result"]
        source_code = prep_res["source_code"]
        module_path = prep_res["module_path"]
        
        print(f"Attempting to heal module: {module_path} for test: {test_case['id']}")
        
        # RAG step: Get context for the specific module
        context_summaries = await query_index(f"all function and class summaries for file {module_path}", top_k=5)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}" for s in context_summaries]) if context_summaries else "No specific context found."

        prompt = f"""
You are an expert AI software engineer. A test case has failed, and your task is to generate a minimal, surgical patch to fix the bug in the source code.

Test Case ID: {test_case['id']}
Test Description: {test_case['description']}
Target Module: {module_path}

Relevant Context from Knowledge Graph:
{context_str}

Source Code to Fix ({module_path}):
--- START SOURCE CODE ---
{source_code}
--- END SOURCE CODE ---

Test Execution Error (stderr):
--- START STDERR ---
{test_result.get('stderr', 'No stderr available.')}
--- END STDERR ---

INSTRUCTIONS:
1. Analyze the error and the source code.
2. Generate a unified diff patch that fixes the bug in the file '{module_path}'.
3. The patch MUST be minimal and only contain the necessary changes.
4. The patch MUST be a valid unified diff format.
5. Respond ONLY with the patch content, enclosed in a single markdown code block with the language set to 'diff'. Do not include any other text, explanation, or markdown formatting outside of the code block.

Example of expected output:
```diff
--- a/src/my_module.py
+++ b/src/my_module.py
@@ -10,7 +10,7 @@
 def calculate(a, b):
-    return a + b
+    return a * b
```
"""
        patch_response = await call_llm(prompt)
        
        # Extract the patch from the LLM response
        patch = ""
        if "```diff" in patch_response:
            patch = patch_response.split("```diff")[1].split("```")[0].strip()
        elif patch_response.strip().startswith("```"):
            patch = patch_response.strip()[3:-3].strip()
            
        # Basic validation: check if it looks like a patch
        if not patch.startswith("--- a/"):
            print("Warning: LLM did not return a valid unified diff patch.")
            return {"status": "FAILED_PATCH_GEN", "patch": None}
            
        return {"status": "PATCH_GENERATED", "patch": patch}

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res.get("status") == "PATCH_GENERATED":
            patch_str = exec_res["patch"]
            module_path = prep_res['module_path']
            repo_path = self.params.get("repo_path")
            
            try:
                # 1. Parse the patch
                patch_set = PatchSet(patch_str)
                if not patch_set:
                    raise ValueError("Patch set is empty or invalid.")
                
                # We expect a patch for a single file, which is the target module
                patch_file = patch_set[0]
                
                # 2. Apply the patch to the file on disk
                full_path = Path(repo_path) / module_path
                original_content = full_path.read_text(encoding='utf-8')
                
                # Apply the patch in memory first to get the new content
                patched_content = original_content
                for hunk in patch_file:
                    patched_content = hunk.apply(patched_content)
                
                # 3. Write the patched content back to the file on disk
                full_path.write_text(patched_content, encoding='utf-8')
                
                # 4. Update the shared state for the next verification node
                # The key for source files in shared["source_files_content"] is the relative path
                relative_module_path = str(Path(module_path).relative_to(repo_path))
                shared["source_files_content"][relative_module_path] = patched_content
                
                shared["generated_patch"] = patch_str
                print(f"✅ Patch successfully applied to {module_path}. Re-verification initiated.")
                return "patch_ready"
                
            except Exception as e:
                print(f"❌ Failed to apply patch to {module_path}: {e}")
                shared["generated_patch"] = None
                return "unpatchable"
        else:
            shared["generated_patch"] = None
            print(f"Healing skipped or failed: {exec_res.get('reason', 'Unknown reason')}")
            return "unpatchable"