import yaml
from pathlib import Path
from pocketflow import AsyncNode, AsyncParallelBatchNode
from utils.async_call_llm import call_llm
from utils.knowledge_graph import query_index
from unidiff import PatchSet
import io
import re
import subprocess
import tempfile
import os


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
- status: "PENDING"
- priority: "HIGH", "MEDIUM", or "LOW", based on the perceived importance of the test.
- description: A concise, one-sentence explanation of the test's purpose.

Project Files:
{', '.join(source_files)}

Respond ONLY with the YAML block for the test plan.
"""
        plan_yaml_str = await call_llm(prompt)
        try:
            if "```yaml" in plan_yaml_str:
                plan_yaml_str = plan_yaml_str.split("```yaml")[1].split("```")[0].strip()
            elif plan_yaml_str.strip().startswith("```"):
                plan_yaml_str = plan_yaml_str.strip()[3:-3].strip()

            plan = yaml.safe_load(plan_yaml_str)
            if not isinstance(plan, dict) or "test_cases" not in plan:
                raise ValueError("Parsed YAML is missing the required 'test_cases' key.")
        except (yaml.YAMLError, IndexError, ValueError) as e:
            print(f"Error parsing test plan YAML from LLM response: {e}")
            raise ValueError("Failed to parse a valid test plan from LLM response.")
        return plan

    async def post_async(self, shared, prep_res, exec_res):
        shared["test_plan"] = exec_res
        tasks = len(exec_res.get("test_cases", []))
        print(f"Test plan created with {tasks} individual test cases.")


class GenerateSingleTestNode(AsyncNode):
    """
    Generates the code for a single test case from the checklist.
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
        context_summaries = await query_index(f"all function and class summaries for file {module_path}", top_k=10)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}" for s in context_summaries]) if context_summaries else "No specific context found."
        framework = project_analysis.get("test_framework", "pytest")

        prompt = f"""
You are an expert Python test engineer. Write a single, runnable test function for the following test case using the `{framework}` framework.

**Test Case Details:**
- Function to write: `def {test_case['id']}(self):` or `def {test_case['id']}():`
- Module to test: `{module_path}`
- Description: `{test_case['description']}`

**Relevant Context from Knowledge Graph:**
---
{context_str}
---

**IMPORTANT INSTRUCTIONS:**
1. Generate ONLY the code for the single test function `{test_case['id']}`.
2. Do NOT generate the full file, class structure, or other test functions.
3. The generated code must be a complete, syntactically correct Python function.
4. Start with `def` and end with the last line of the function's code. Do not use markdown.
"""
        test_code = await call_llm(prompt)

        if "```python" in test_code:
            test_code = test_code.split("```python")[1].split("```")[0].strip()
        elif test_code.strip().startswith("```"):
            test_code = test_code.strip()[3:-3].strip()

        try:
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

        if test_file_path in shared["generated_files"]:
            shared["generated_files"][test_file_path] += f"\n\n{new_code}"
        else:
            shared["generated_files"][test_file_path] = f"# Test file for {prep_res['test_case']['module_path']}\nimport pytest\n\n{new_code}"

        print(f"Appended test case {exec_res['test_case_id']} to in-memory file {test_file_path}")


class HealNode(AsyncNode):
    """
    An autonomous agent that attempts to fix a single failing test case.
    """
    def _extract_focused_error(self, stdout: str, stderr: str) -> str:
        output = stdout + "\n" + stderr
        if not output.strip() or "No STDOUT captured" in output:
            return "No error output was provided."
        summary_match = re.search(r"_{10,} short test summary info _{10,}([\s\S]*)", output)
        if summary_match:
            return f"The test failed. The most relevant summary is:\n\n{summary_match.group(1).strip()}"
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
        # Add repo_path to prep_res to allow lazy-loading files from disk
        return {
            "failure_context": shared.get("failure_context"),
            "repo_path": shared.get("repo_path")
        }

    async def exec_async(self, prep_res):
        failure_context = prep_res.get("failure_context")
        if not failure_context:
            raise ValueError("HealNode requires 'failure_context'.")

        print("Engaging the healing agent...")
        focused_error = self._extract_focused_error(failure_context.get('stdout', ''), failure_context.get('stderr', ''))
        test_case_id = failure_context.get("test_case_id")
        print(f"Focused Error Context for LLM:\n---\n{focused_error}\n---")

        query_text = f"Code relevant to this test failure in test '{test_case_id}': {focused_error}"
        relevant_docs = await query_index(query_text, top_k=3)
        context_str = "\n---\n".join([f"Path: {s['file_path']}\nUnit: {s['unit_name']}\nSummary: {s['summary']}\nCode Snippet:\n{s['code']}" for s in relevant_docs])

        prompt = f"""
You are an expert Python debugger. A test function `{test_case_id}` failed.
Analyze the error and code to generate a patch in `git diff` format.
The bug could be in the test code OR the source code. You must decide which to fix.
If you need to create a new file (like a `conftest.py`), use `/dev/null` as the original file path.

**Focused Test Failure:**
---
{focused_error}
---

**Relevant Code Context:**
---
{context_str}
---

**Your Task:**
Respond ONLY with a YAML block containing your reasoning and the patch.

Example for modifying a file:
```yaml
reasoning: |
  The test failed due to an off-by-one error in the source code's loop. I will correct the range.
file_to_patch: "src/logic/calculator.py"
patch: |
  --- a/src/logic/calculator.py
  +++ b/src/logic/calculator.py
  @@ -10,7 +10,7 @@
   def sum_numbers(n):
       total = 0
  -    for i in range(n):
  +    for i in range(n + 1):
           total += i
       return total
```

Example for creating a new file:
```yaml
reasoning: |
  The test failed because the `client` fixture is missing. I will create a `conftest.py` file to provide this standard Flask fixture.
file_to_patch: "tests/examples/tutorial/flaskr/conftest.py"
patch: |
  --- /dev/null
  +++ b/tests/examples/tutorial/flaskr/conftest.py
  @@ -0,0 +1,13 @@
  +import pytest
  +from flaskr import create_app
  +
  +@pytest.fixture
  +def app():
  +    app = create_app({{"TESTING": True}})
  +    yield app
  +
  +@pytest.fixture
  +def client(app):
  +    return app.test_client()
```
"""
        response_yaml = await call_llm(prompt)
        try:
            if "```yaml" in response_yaml:
                response_yaml = response_yaml.split("```yaml")[1].split("```")[0].strip()
            parsed = yaml.safe_load(response_yaml)
            if not all(k in parsed for k in ["reasoning", "file_to_patch", "patch"]):
                raise ValueError("Response missing required keys.")
            return parsed
        except (yaml.YAMLError, IndexError, ValueError) as e:
            print(f"Error parsing healing patch YAML: {e}")
            return {
                "file_to_patch": None,
                "patch": None,
                "reasoning": "Failed to generate valid patch YAML."
            }

    async def post_async(self, shared, prep_res, exec_res):
        file_to_patch_rel = exec_res.get("file_to_patch")  # Relative path
        patch_str = exec_res.get("patch")
        repo_path = prep_res.get("repo_path")  # Absolute path to repo

        if not file_to_patch_rel or not patch_str or not repo_path:
            print("❌ Healing agent did not provide a valid patch or file path.")
            return "unpatchable"

        print(f"Healing agent generated a patch for: {file_to_patch_rel}")
        print(f"Reasoning: {exec_res['reasoning'].strip()}")

        # Determine if the file is a test or source file and get its content
        is_new_file = '--- /dev/null' in patch_str
        source_content = None
        target_store = None

        if file_to_patch_rel in shared.get("generated_files", {}):
            target_store = shared["generated_files"]
            source_content = target_store[file_to_patch_rel]
            print(f"Found file to patch in in-memory generated tests: {file_to_patch_rel}")
        elif file_to_patch_rel in shared.get("source_files_content", {}):
            target_store = shared["source_files_content"]
            source_content = target_store[file_to_patch_rel]
            print(f"Found file to patch in in-memory source code: {file_to_patch_rel}")
        elif not is_new_file:
            # --- LAZY LOADING ---
            # File not in memory, try loading it from disk
            full_path_on_disk = Path(repo_path) / file_to_patch_rel
            if full_path_on_disk.exists():
                print(f"Lazy loading file from disk: {full_path_on_disk}")
                with open(full_path_on_disk, 'r', encoding='utf-8') as f:
                    source_content = f.read()
                # Decide where to store it if patched
                if "source_files_content" not in shared:
                    shared["source_files_content"] = {}
                if "generated_files" not in shared:
                    shared["generated_files"] = {}
                target_store = shared["source_files_content"] if file_to_patch_rel.startswith('src') else shared["generated_files"]
            else:
                print(f"❌ File to patch '{file_to_patch_rel}' not found in memory or on disk.")
                return "unpatchable"

        # --- ROBUST PATCH APPLICATION using command-line `patch` utility ---
        patch_file_path = None
        original_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.patch') as patch_file, \
                 tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.original') as original_file:
                
                original_file_path = original_file.name
                patch_file_path = patch_file.name

                if not is_new_file:
                    original_file.write(source_content)
                    original_file.flush()
                
                patch_file.write(patch_str)
                patch_file.flush()

                # The `patch` command is more robust than Python libraries for slightly malformed diffs
                cmd = ["patch", original_file_path, "-i", patch_file_path, "-o", f"{original_file_path}.patched"]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    raise RuntimeError(f"The `patch` command failed: {result.stderr}")
                
                with open(f"{original_file_path}.patched", 'r', encoding='utf-8') as f:
                    patched_content = f.read()

            # Update the correct in-memory store
            if is_new_file:
                # If it's a new file, it must be a test-related file (like conftest.py)
                if "generated_files" not in shared:
                    shared["generated_files"] = {}
                shared["generated_files"][file_to_patch_rel] = patched_content
            else:
                target_store[file_to_patch_rel] = patched_content
            
            action = "created" if is_new_file else "patched"
            print(f"✅ File successfully {action} in-memory. Retrying verification.")
            return "patched"

        except Exception as e:
            print(f"❌ Failed to apply patch: {e}")
            return "unpatchable"
        finally:
            # Clean up temp files
            if patch_file_path and os.path.exists(patch_file_path):
                os.remove(patch_file_path)
            if original_file_path:
                if os.path.exists(original_file_path):
                    os.remove(original_file_path)
                if os.path.exists(f"{original_file_path}.patched"):
                    os.remove(f"{original_file_path}.patched")