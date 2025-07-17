import yaml
from pathlib import Path
from pocketflow import AsyncNode, AsyncParallelBatchNode
from utils.async_call_llm import call_llm
from utils.knowledge_graph import query_index


class PlanTestsNode(AsyncNode):
    """
    An intelligent agent that queries the KG to create a high-level,
    strategic test plan for the entire codebase.
    """
    async def prep_async(self, shared):
        project_analysis = shared.get("project_analysis", {})
        return project_analysis

    async def exec_async(self, prep_res):
        project_analysis = prep_res
        print("Planning test suite...")

        source_files = project_analysis.get("source_files", [])
        if not source_files:
            raise ValueError("No source files found in project_analysis to create a test plan.")

        prompt = f"""
You are a senior test architect. Based on the following list of source files from a project, create a strategic test plan.

Your plan must be in YAML format and include two main sections:
1.  `unit_test_tasks`: A list of tasks. For each task, specify the `module` to test and a list of its internal `dependencies_to_mock`.
2.  `integration_test_tasks`: A list of 1-2 critical integration tests that verify interactions between the most important modules. Provide a `name` and `description` for each.

Project Files:
{', '.join(source_files)}

Respond ONLY with the YAML block for the test plan.
"""
        plan_yaml_str = await call_llm(prompt)

        try:
            plan = yaml.safe_load(plan_yaml_str.split("```yaml")[1].split("```")[0].strip())
            if not isinstance(plan, dict) or "unit_test_tasks" not in plan:
                raise ValueError("Parsed YAML is missing 'unit_test_tasks' key.")
        except (yaml.YAMLError, IndexError, ValueError) as e:
            print(f"Error parsing test plan YAML: {e}")
            raise ValueError("Failed to parse a valid test plan from LLM response.")

        return plan

    async def post_async(self, shared, prep_res, exec_res):
        shared["test_plan"] = exec_res
        unit_tasks = len(exec_res.get("unit_test_tasks", []))
        integration_tasks = len(exec_res.get("integration_test_tasks", []))
        print(f"Test plan created: {unit_tasks} unit tasks, {integration_tasks} integration tasks.")


class GenerateUnitTestsNode(AsyncParallelBatchNode):
    """
    Generates unit tests for each module defined in the test plan.
    This node uses RAG to provide relevant context to the LLM for each test file.
    """
    async def prep_async(self, shared):
        shared["generated_files"] = {}
        if not shared.get("test_plan") or not shared["test_plan"].get("unit_test_tasks"):
            print("Warning: No unit test tasks found in plan. Skipping generation.")
            return []

        project_analysis = shared.get("project_analysis", {})
        tasks = shared["test_plan"]["unit_test_tasks"]
        return [(task, project_analysis) for task in tasks]

    async def exec_async(self, item):
        task, project_analysis = item
        module_path = task.get("module")
        if not module_path:
            return {}

        print(f"Generating unit tests for: {module_path}")

        context_summaries = await query_index(
            f"all function and class summaries for file {module_path}", top_k=10
        )

        if not context_summaries:
            context_str = "No specific context found. Generate tests based on the file path and general programming principles."
        else:
            context_str = "\n---\n".join([
                f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}"
                for s in context_summaries
            ])

        framework = project_analysis.get("test_framework", "pytest")

        prompt = f"""
You are an expert Python test engineer. Write a complete, runnable unit test file for module '{module_path}' using the `{framework}` framework.

Relevant context from the knowledge graph:
---
{context_str}
---

Generate only pure Python code. Do not include explanations or markdown formatting.
"""
        test_code = await call_llm(prompt)

        if test_code.strip().startswith("```python"):
            test_code = test_code.split("```python")[1].split("```")[0].strip()
        elif test_code.strip().startswith("```"):
            test_code = test_code.strip()[3:-3].strip()

        test_file_path = f"tests/test_{Path(module_path).stem}.py"
        return {test_file_path: test_code}

    async def post_async(self, shared, prep_res, exec_res_list):
        for file_dict in exec_res_list:
            shared["generated_files"].update(file_dict)
        print(f"Generated {len(exec_res_list)} unit test files.")


class HealNode(AsyncNode):
    """
    An autonomous agent that attempts to fix failing tests by analyzing the error
    and querying the knowledge graph for context.
    """
    async def prep_async(self, shared):
        return shared.get("failure_context")

    async def exec_async(self, prep_res):
        failure_context = prep_res
        if not failure_context:
            raise ValueError("HealNode requires 'failure_context' to be in the shared store.")

        print("A test failed. Engaging the healing agent...")

        query_text = f"Code relevant to this test failure: {failure_context.get('stderr', 'No error output.')}"
        relevant_docs = await query_index(query_text, top_k=3)

        context_str = "\n---\n".join([
            f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}\nCode:\n{s['code']}"
            for s in relevant_docs
        ])

        prompt = f"""
You are an expert debugger. A test run failed. Analyze the error and relevant code to generate a patch.
The bug could be in the test code OR the source code. You must decide which to fix.

Test Failure:
---
{failure_context.get('stderr', 'N/A')}
---

Relevant Code Context:
---
{context_str}
---

Your task: Provide a patch in git diff format. Identify the correct file path.
Respond ONLY with a YAML block:
```yaml
reasoning: |
  The test failed because of an off-by-one error. The test is correct; the source code is buggy. I will patch the source file.
file_to_patch: "src/utils.py"
patch: |
  --- a/src/utils.py
  +++ b/src/utils.py
  @@ -1,1 +1,1 @@
  - buggy line
  + fixed line
"""
        response_yaml = await call_llm(prompt)

        try:
            parsed = yaml.safe_load(response_yaml.split("```yaml")[1].split("```")[0].strip())
            if not all(k in parsed for k in ["reasoning", "file_to_patch", "patch"]):
                raise ValueError("HealNode LLM response missing required keys.")
        except (yaml.YAMLError, IndexError, ValueError) as e:
            print(f"Error parsing healing patch YAML: {e}")
            return {
                "file_to_patch": None,
                "patch": None,
                "reasoning": "Failed to generate a valid patch."
            }

        return parsed

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res and exec_res.get("file_to_patch") and exec_res.get("patch"):
            print(f"Healing agent generated a patch for: {exec_res['file_to_patch']}")
            print(f"Reasoning: {exec_res['reasoning'].strip()}")
            shared["last_patch_attempt"] = exec_res['patch']
        else:
            print("Healing agent could not generate a valid patch. Retrying without changes.")
            shared["last_patch_attempt"] = None
