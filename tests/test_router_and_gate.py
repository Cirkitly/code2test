import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from code2test.nodes.generation_nodes import MultiToolRouterNode
from code2test.nodes.verification_nodes import QualityGateNode
from pocketflow import SharedStore

# Mock dependencies for MultiToolRouterNode
@pytest.fixture
def mock_query_index():
    with patch('code2test.nodes.generation_nodes.query_index', new_callable=AsyncMock) as mock:
        mock.return_value = [
            {"file_path": "src/module.py", "unit_name": "func_a", "summary": "Summary A"},
            {"file_path": "src/module.py", "unit_name": "func_b", "summary": "Summary B"},
        ]
        yield mock

@pytest.fixture
def router_node():
    return MultiToolRouterNode()

@pytest.mark.asyncio
async def test_router_node_prep_high_priority(router_node, mock_query_index):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_high", "priority": "HIGH", "module_path": "src/module.py"}
    shared["project_analysis"] = {"test_framework": "pytest"}
    
    prep_res = await router_node.prep_async(shared)
    
    assert prep_res is not None
    assert prep_res["strategy"]["name"] == "High-Priority Strategy (Detailed)"
    assert prep_res["strategy"]["confidence_target"] == 0.95
    assert "Summary A" in prep_res["context_str"]
    mock_query_index.assert_called_once()

@pytest.mark.asyncio
async def test_router_node_post(router_node, mock_query_index):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_medium", "priority": "MEDIUM", "module_path": "src/module.py"}
    shared["project_analysis"] = {"test_framework": "pytest"}
    
    prep_res = await router_node.prep_async(shared)
    exec_res = prep_res # exec_async is a passthrough for now
    
    await router_node.post_async(shared, prep_res, exec_res)
    
    assert "generation_context" in shared
    assert shared["generation_context"]["strategy"]["name"] == "Medium-Priority Strategy (Standard)"
    assert shared["current_test_case"]["confidence_target"] == 0.85

# Unit tests for QualityGateNode
@pytest.fixture
def gate_node():
    return QualityGateNode()

@pytest.mark.asyncio
async def test_quality_gate_pass(gate_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_pass", "confidence_target": 0.85}
    shared["generated_files"] = {"tests/test_file.py": "def test_pass():\n    assert True"}
    shared["current_test_case"]["test_file_path"] = "tests/test_file.py"
    
    prep_res = gate_node.prep(shared)
    exec_res = gate_node.exec(prep_res)
    
    assert exec_res["passed"] is True
    assert exec_res["reason"] == "All checks passed."
    
    post_res = gate_node.post(shared, prep_res, exec_res)
    assert post_res == "success"

@pytest.mark.asyncio
async def test_quality_gate_fail_length(gate_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_fail_length", "confidence_target": 0.85}
    long_code = "\n".join([f"line_{i}" for i in range(60)])
    shared["generated_files"] = {"tests/test_file.py": long_code}
    shared["current_test_case"]["test_file_path"] = "tests/test_file.py"
    
    prep_res = gate_node.prep(shared)
    exec_res = gate_node.exec(prep_res)
    
    assert exec_res["passed"] is False
    assert "Code complexity too high" in exec_res["reason"]
    
    post_res = gate_node.post(shared, prep_res, exec_res)
    assert post_res == "failure"
    assert "Quality Gate Failed" in shared["current_test_case_result"]["stderr"]

@pytest.mark.asyncio
async def test_quality_gate_fail_confidence(gate_node):
    shared = SharedStore()
    # Assumed confidence is 0.90 in the node, so setting target higher will fail
    shared["current_test_case"] = {"id": "test_fail_conf", "confidence_target": 0.99}
    shared["generated_files"] = {"tests/test_file.py": "def test_fail_conf():\n    assert True"}
    shared["current_test_case"]["test_file_path"] = "tests/test_file.py"
    
    prep_res = gate_node.prep(shared)
    exec_res = gate_node.exec(prep_res)
    
    assert exec_res["passed"] is False
    assert "Generation confidence too low" in exec_res["reason"]
    
    post_res = gate_node.post(shared, prep_res, exec_res)
    assert post_res == "failure"
