import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from code2test.nodes.generation_nodes import HealNode
from code2test.nodes.verification_nodes import HumanInTheLoopNode
from pocketflow import SharedStore

# Mock dependencies for HealNode
@pytest.fixture
def mock_heal_dependencies():
    with patch('code2test.nodes.generation_nodes.query_index', new_callable=AsyncMock) as mock_query, \
         patch('code2test.nodes.generation_nodes.call_llm', new_callable=AsyncMock) as mock_llm:
        mock_query.return_value = [
            {"file_path": "src/module.py", "unit_name": "func_a", "summary": "Summary A"},
        ]
        # Mock LLM to return a valid unified diff patch
        mock_llm.return_value = """
--- src/module.py
+++ src/module.py
@@ -1,4 +1,4 @@
-def buggy_func():
-    return 1
+def buggy_func():
+    return 2
"""
        yield mock_query, mock_llm

@pytest.fixture
def heal_node():
    return HealNode()

@pytest.mark.asyncio
async def test_heal_node_prep_and_exec(heal_node, mock_heal_dependencies):
    mock_query, mock_llm = mock_heal_dependencies
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_buggy", "module_path": "src/module.py"}
    shared["current_test_case_result"] = {"passed": False, "stderr": "AssertionError: 1 != 2"}
    shared["project_analysis"] = {}
    
    # Mock the source file content
    shared["source_files_content"] = {"src/module.py": "def buggy_func():\n    return 1\n"}
    
    prep_res = await heal_node.prep_async(shared)
    assert prep_res is not None
    
    exec_res = await heal_node.exec_async(prep_res)
    assert "patch" in exec_res
    assert "buggy_func" in exec_res["patch"]
    mock_llm.assert_called_once()

@pytest.mark.asyncio
async def test_heal_node_post_success(heal_node, mock_heal_dependencies):
    mock_query, mock_llm = mock_heal_dependencies
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_buggy", "module_path": "src/module.py"}
    shared["current_test_case_result"] = {"passed": False, "stderr": "AssertionError: 1 != 2"}
    shared["project_analysis"] = {}
    shared["source_files_content"] = {"src/module.py": "def buggy_func():\n    return 1\n"}
    
    prep_res = await heal_node.prep_async(shared)
    exec_res = await heal_node.exec_async(prep_res)
    
    # Mock the patch application to succeed
    with patch('code2test.nodes.generation_nodes.PatchSet.apply') as mock_apply:
        mock_apply.return_value = True
        await heal_node.post_async(shared, prep_res, exec_res)
    
    assert shared["generated_patch"] == exec_res["patch"]
    assert "src/module.py" in shared["source_files_content"]
    # The content should be the patched content, but since we mocked apply, we just check for the key
    
# Unit tests for HumanInTheLoopNode
@pytest.fixture
def human_node():
    return HumanInTheLoopNode()

@pytest.mark.asyncio
async def test_human_node_prep_quality_gate_failure(human_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_gate_fail", "module_path": "src/module.py"}
    shared["current_test_case_result"] = {"passed": False, "stderr": "Quality Gate Failed: Code complexity too high"}
    
    prep_res = human_node.prep(shared)
    
    assert prep_res["reason"] == "Quality Gate Failure"
    assert prep_res["test_case"]["id"] == "test_gate_fail"

@pytest.mark.asyncio
async def test_human_node_prep_healing_failed(human_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_heal_fail", "module_path": "src/module.py"}
    shared["current_test_case_result"] = {"passed": False, "stderr": "AssertionError: 1 != 2"}
    shared["generated_patch"] = "diff -u..."
    
    prep_res = human_node.prep(shared)
    
    assert prep_res["reason"] == "Healing Failed (Patch did not fix the issue)"
    assert prep_res["generated_patch"] == "diff -u..."

@pytest.mark.asyncio
async def test_human_node_exec_and_post(human_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_escalate", "module_path": "src/module.py"}
    shared["current_test_case_result"] = {"passed": False, "stderr": "Unknown Error"}
    
    prep_res = human_node.prep(shared)
    exec_res = human_node.exec(prep_res)
    
    assert exec_res["status"] == "ESCALATED"
    assert "Human review is required" in exec_res["report"]["action_required"]
    
    post_res = human_node.post(shared, prep_res, exec_res)
    
    assert post_res == "escalated"
    assert shared["current_test_case"]["status"] == "ESCALATED"
    assert shared["current_test_case"]["escalation_reason"] == "Initial Verification Failed (Unattempted Healing)"
