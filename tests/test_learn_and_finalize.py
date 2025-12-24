import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from code2test.nodes.generation_nodes import LearningEngineNode
from code2test.nodes.verification_nodes import FinalizeAndOrganizeNode
from pocketflow import SharedStore
from pathlib import Path

# Unit tests for LearningEngineNode
@pytest.fixture
def learn_node():
    return LearningEngineNode()

@pytest.mark.asyncio
async def test_learning_node_success(learn_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_success", "status": "PASSED"}
    shared["current_test_case_result"] = {"passed": True}
    shared["generation_context"] = {"strategy": {"name": "Standard", "confidence_target": 0.85}}
    
    prep_res = await learn_node.prep_async(shared)
    exec_res = await learn_node.exec_async(prep_res)
    
    assert exec_res["status"] == "LEARNING_COMPLETE"
    
@pytest.mark.asyncio
async def test_learning_node_escalated(learn_node):
    shared = SharedStore()
    shared["current_test_case"] = {"id": "test_escalated", "status": "ESCALATED", "escalation_reason": "Quality Gate Failure"}
    shared["current_test_case_result"] = {"passed": False}
    shared["generation_context"] = {"strategy": {"name": "High-Priority", "confidence_target": 0.95}}
    
    prep_res = await learn_node.prep_async(shared)
    exec_res = await learn_node.exec_async(prep_res)
    
    assert exec_res["status"] == "LEARNING_COMPLETE"

# Unit tests for FinalizeAndOrganizeNode
@pytest.fixture
def finalize_node():
    return FinalizeAndOrganizeNode()

@pytest.fixture
def mock_filesystem(tmp_path):
    # Mock Path to use a temporary directory for file writing
    with patch('code2test.nodes.verification_nodes.Path') as MockPath:
        # Configure the mock Path to behave like the real Path for the repo_path
        MockPath.return_value = tmp_path
        MockPath.side_effect = lambda *args: Path(tmp_path, *args)
        yield MockPath

def test_finalize_node_prep(finalize_node):
    shared = SharedStore()
    shared["repo_path"] = "/mock/repo"
    shared["generated_files"] = {"tests/file.py": "content"}
    shared["final_result"] = "Success"
    shared["test_plan"] = {"test_cases": [{"id": "t1", "status": "PASSED"}]}
    
    prep_res = finalize_node.prep(shared)
    
    assert prep_res["repo_path"] == "/mock/repo"
    assert "tests/file.py" in prep_res["files_to_write"]
    assert len(prep_res["test_plan"]) == 1

def test_finalize_node_generate_quality_report(finalize_node):
    test_plan = [
        {"id": "t1", "status": "PASSED"},
        {"id": "t2", "status": "ESCALATED", "escalation_reason": "Quality Gate Failure", "last_error": "Error log..."},
        {"id": "t3", "status": "FAILED"},
    ]
    report = finalize_node._generate_quality_report(test_plan)
    
    assert "Total Test Cases Planned | 3" in report
    assert "Tests Successfully Generated & Verified | 1" in report
    assert "Tests Escalated for Human Review | 1" in report
    assert "Tests Failed (Unresolved) | 1" in report
    assert "Quality Gate Failure" in report

def test_finalize_node_generate_audit_trail(finalize_node):
    test_plan = [
        {"id": "t1", "status": "PASSED", "module_path": "src/a.py"},
        {"id": "t2", "status": "ESCALATED", "escalation_reason": "Healing Failed", "last_error": "Error log..."},
    ]
    trail = finalize_node._generate_audit_trail(test_plan)
    
    assert "Test Generation Audit Trail" in trail
    assert "Test Case: t1" in trail
    assert "Final Status | PASSED" in trail
    assert "Test Case: t2" in trail
    assert "Escalation Reason | Healing Failed" in trail
    assert "Error log..." in trail

def test_finalize_node_exec_writes_files(finalize_node, tmp_path):
    # Use a real temporary path for this test
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    test_file_path = "tests/new_test.py"
    report_path = "quality_report.md"
    
    prep_res = {
        "repo_path": str(repo_path),
        "files_to_write": {test_file_path: "def test_new(): pass"},
        "test_plan": [{"id": "t1", "status": "PASSED"}],
        "final_result_message": "Done"
    }
    
    exec_res = finalize_node.exec(prep_res)
    
    assert exec_res == "Done"
    
    # Check if files were written
    assert (repo_path / test_file_path).exists()
    assert (repo_path / report_path).exists()
    assert (repo_path / "audit_trail.md").exists()
    
    # Check if __init__.py was created
    assert (repo_path / "tests" / "__init__.py").exists()
    
    with open(repo_path / test_file_path, 'r') as f:
        assert "def test_new(): pass" in f.read()
