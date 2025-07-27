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
    concurrency = 5

    async def prep_async(self, shared):
        shared["generated_files"] = {} 
        shared["source_files_content"] = {}
        if not shared.get("test_plan") or not shared["test_plan"].get("unit_test_tasks"):
            print("Warning: No unit test tasks found in plan. Skipping generation.")
            return []
        project_analysis = shared.get("project_analysis", {})
        tasks = shared["test_plan"]["unit_test_tasks"]
        repo_path = self.params.get("repo_path")
        print(f"Generating {len(tasks)} unit test files with concurrency={self.concurrency}...")
        return [(task, project_analysis, repo_path) for task in tasks]
    
    async def exec_async(self, item):
        task, project_analysis, repo_path = item
        module_path = task.get("module")
        if not module_path: return {}

        print(f"Generating unit tests for: {module_path}")
        context_summaries = await query_index(f"all function and class summaries for file {module_path}", top_k=10)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}" for s in context_summaries]) if context_summaries else "No specific context found."
        
        framework = project_analysis.get("test_framework", "pytest")
        
        prompt = f"""
You are an expert Python test engineer. Write a complete, runnable unit test file for module '{module_path}' using the `{framework}` framework.

**IMPORTANT RULES FOR IMPORTS:**
1.  All imports of project code must be relative to the project root. For a file at `path/to/module.py`, the import should be `from path.to import module`.
2.  When generating an import statement from a file path, you MUST replace any hyphens (`-`) in the path with underscores (`_`). For example, to import from `cookbook/pocketflow-agent/utils.py`, the correct import is `from cookbook.pocketflow_agent import utils`.
3.  Do NOT use `importlib` or any other dynamic import mechanisms. Use standard, static `import` and `from` statements.

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

        try:
            relative_module_path = Path(module_path).relative_to(repo_path)
            test_filename = f"test_{relative_module_path.name}"
            test_file_path = str(Path("tests") / relative_module_path.parent / test_filename)
        except ValueError:
            test_file_path = f"tests/test_{Path(module_path).name}"
        return {test_file_path: test_code}
    
    async def post_async(self, shared, prep_res, exec_res_list):
        init_files_to_add = set()
        for file_dict in exec_res_list:
            for path_str in file_dict.keys():
                shared["generated_files"].update(file_dict)
                p = Path(path_str).parent
                # Traverse up to the 'tests' directory, adding __init__.py
                while p != Path('.') and 'tests' in p.parts:
                    init_file = p / "__init__.py"
                    init_files_to_add.add(str(init_file))
                    if p.name == 'tests': break
                    p = p.parent
        
        for init_file in init_files_to_add:
            if init_file not in shared["generated_files"]:
                shared["generated_files"][init_file] = "# Auto-generated by AI Software Foundry\n"
        
        print(f"\nGenerated {len(shared['generated_files'])} total files (including __init__.py).")


class HealNode(AsyncNode):
    """
    An autonomous agent that attempts to fix failing tests by analyzing the error,
    querying the knowledge graph for context, and applying a patch in-memory.
    """
    def _extract_focused_error(self, stdout: str, stderr: str) -> str:
        output = stdout + "\n" + stderr
        if not output.strip() or "No STDOUT captured" in output:
             return "No error output was provided."

        interruption_match = re.search(r"!!!! (Interrupted:.*) !!!!", output)
        if interruption_match:
            return f"Test collection was interrupted. This is the highest priority error:\n\n{interruption_match.group(1)}"

        failure_summary_match = re.search(r"=+ (FAILURES|ERRORS) =+([\s\S]*)___+ short test summary info ___", output)
        if failure_summary_match:
            section_type = failure_summary_match.group(1)
            full_trace = failure_summary_match.group(2).strip()
            first_trace = full_trace.split("\n_")[0]
            return f"The test suite reported {section_type}. Here is the first full traceback:\n\n{first_trace}"

        if len(output) > 2000:
            return f"The test output is very long. Here is the beginning:\n\n{output[:2000]}..."
        
        return output

    async def prep_async(self, shared):
        return shared.get("failure_context")

    async def exec_async(self, prep_res):
        failure_context = prep_res
        if not failure_context: raise ValueError("HealNode requires 'failure_context'")

        print("A test failed. Engaging the healing agent...")
        raw_stdout = failure_context.get('stdout', '')
        raw_stderr = failure_context.get('stderr', '')
        focused_error = self._extract_focused_error(raw_stdout, raw_stderr)
        
        print(f"Focused Error Context for LLM:\n---\n{focused_error}\n---")
        
        query_text = f"Code relevant to this test failure: {focused_error}"
        relevant_docs = await query_index(query_text, top_k=3)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}\nCode:\n{s['code']}" for s in relevant_docs])
        prompt = f"""
You are an expert debugger. A test run failed. I have extracted the most likely root cause.
Analyze this focused error and the relevant code context to generate a patch.
The bug could be in the test code OR the source code. You must decide which to fix.

Focused Test Failure:
---
{focused_error}
---

Relevant Code Context:
---
{context_str}
---

Your task: Provide a patch in git diff format. Identify the correct file path relative to the project root. If you need to create a new file, the patch should be relative to `/dev/null`.
Respond ONLY with a YAML block:
```yaml
reasoning: |
  The test failed because of an ImportError. The test file is trying to import a module from the wrong relative path. I will correct the import statement in the test file.
file_to_patch: "tests/test_some_module.py"
patch: |
  --- a/tests/test_some_module.py
  +++ b/tests/test_some_module.py
  @@ -1,1 +1,1 @@
  - from ..wrong import thing
  + from project.correct import thing
"""
        response_yaml = await call_llm(prompt)
        try:
            parsed = yaml.safe_load(response_yaml.split("```yaml")[1].split("```")[0].strip())
            if not all(k in parsed for k in ["reasoning", "file_to_patch", "patch"]):
                raise ValueError("HealNode LLM response missing required keys.")
        except (yaml.YAMLError, IndexError, ValueError) as e:
            print(f"Error parsing healing patch YAML: {e}")
            return { "file_to_patch": None, "patch": None, "reasoning": "Failed to generate a valid patch." }
        return parsed

    async def post_async(self, shared, prep_res, exec_res):
        if not (exec_res and exec_res.get("file_to_patch") and exec_res.get("patch")):
            print("❌ Healing agent could not generate a valid patch. Cannot continue.")
            shared["final_result"] = "Healing failed: LLM did not produce a valid patch."
            return "unpatchable"
        
        file_to_patch = exec_res['file_to_patch']
        patch_str = exec_res['patch']
        print(f"Healing agent generated a patch for: {file_to_patch}")
        print(f"Reasoning: {exec_res['reasoning'].strip()}")
        
        if file_to_patch in shared.get("generated_files", {}):
            target_store = shared["generated_files"]
            source_content = target_store[file_to_patch]
            print(f"Attempting to patch in-memory test file: {file_to_patch}")
        elif file_to_patch in shared.get("source_files_content", {}):
            target_store = shared["source_files_content"]
            source_content = target_store[file_to_patch]
            print(f"Attempting to patch in-memory source file: {file_to_patch}")
        else:
            target_store = shared["generated_files"]
            source_content = ""
            print(f"File '{file_to_patch}' not found. Attempting to create it with the patch.")

        try:
            # --- FINAL FIX: CORRECTLY APPLY THE PATCH ---
            # Parse the patch string
            patch_set = PatchSet(io.StringIO(patch_str))
            
            # Check if the patch is valid
            if not patch_set:
                raise ValueError("Patch string was empty or invalid.")
            
            patched_file = patch_set[0]

            # Reconstruct the file line by line based on the patch instructions
            source_lines = source_content.splitlines(True)
            patched_lines = []
            source_line_idx = 0

            for hunk in patched_file:
                # The hunk's source_start gives the 1-based line number.
                # We advance our source_line_idx to match it.
                while source_line_idx < hunk.source_start - 1 and source_line_idx < len(source_lines):
                    patched_lines.append(source_lines[source_line_idx])
                    source_line_idx += 1
                
                for line in hunk:
                    if line.is_added:
                        patched_lines.append(line.value[1:])
                    elif line.is_context:
                        patched_lines.append(line.value[1:])
                        source_line_idx += 1
                    elif line.is_removed:
                        source_line_idx += 1 # Just skip this line from the source
            
            # Add any remaining lines from the original file (for patches that don't go to the end)
            while source_line_idx < len(source_lines):
                patched_lines.append(source_lines[source_line_idx])
                source_line_idx += 1

            patched_content = "".join(patched_lines)
            
            # Update the in-memory file
            target_store[file_to_patch] = patched_content
            
            action = "created" if not source_content else "patched"
            print(f"✅ File successfully {action} in-memory. Retrying verification.")
            return "patched"
        except Exception as e:
            print(f"❌ Failed to apply patch: {e}")
            shared["final_result"] = f"Healing failed: Could not apply patch to '{file_to_patch}': {e}"
            return "unpatchable"