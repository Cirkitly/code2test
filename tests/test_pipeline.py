"""End-to-end tests for the generate -> write -> verify -> repair pipeline, using scripted models."""

import asyncio
from pathlib import Path
from typing import Iterable, List

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from code2test.agents import test_agent as test_agent_mod
from code2test.core import generator as generator_mod
from code2test.core.models import GenerationConfig
from code2test.src.be.dependency_analyzer import DependencyGraphBuilder
from code2test.src.config import Config

SOURCE = '''
def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b
'''

PASSING = "def test_add():\n    assert add(2, 3) == 5\n"
FAILING = "def test_add():\n    assert add(2, 3) == 6\n"


def scripted(replies: Iterable[dict]) -> FunctionModel:
    """A model that answers each structured-output request with the next scripted reply."""
    queue: List[dict] = list(replies)
    prompts: List[str] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts.append(str(messages[-1]))
        args = queue.pop(0) if len(queue) > 1 else queue[0]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    model = FunctionModel(respond)
    model.prompts = prompts  # type: ignore[attr-defined]
    return model


def tests_reply(code: str, imports=("from calc.ops import add",)) -> dict:
    return {
        "tests": [{"name": "test_add", "description": "adds", "test_code": code, "tests_behavior": "sum"}],
        "imports": list(imports),
    }


def diagnosis_reply(cause: str) -> dict:
    return {"cause": cause, "confidence": 0.9, "explanation": "add returns the wrong value"}


def _make_repo(tmp_path: Path, src_layout: bool = False) -> Path:
    pkg = tmp_path / ("src/calc" if src_layout else "calc")
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "ops.py").write_text(SOURCE)
    return tmp_path


def _components(repo: Path) -> dict:
    """Build component dicts the same way the `test` CLI command does."""
    config = Config(
        repo_path=str(repo),
        output_dir=str(repo / "tests"),
        dependency_graph_dir=str(repo / ".code2test" / "dependency_graphs"),
        docs_dir=str(repo / ".code2test" / "docs"),
        max_depth=2,
        llm_base_url="",
        llm_api_key="",
        main_model="",
        cluster_model="",
        agent_instructions={"include_patterns": None, "exclude_patterns": ["tests", "test_*.py"]},
    )
    nodes, _ = DependencyGraphBuilder(config).build_dependency_graph()
    components = {}
    for key, node in nodes.items():
        data = node.model_dump()
        data["dependencies"] = list(data.get("depends_on", []))
        components[key] = data
    return components


def _run(repo: Path, test_model: FunctionModel, diagnosis_model: FunctionModel = None):
    gen = generator_mod.TestGenerator(
        repo_path=str(repo),
        config=GenerationConfig(auto_accept=True, confidence_threshold=0.0, output_dir="tests"),
    )
    gen.test_agent.model = test_model
    gen.diagnosis_agent.model = diagnosis_model or scripted([diagnosis_reply("TEST_WRONG")])
    return asyncio.run(gen.generate_tests_for_module(str(repo), _components(repo)))


def test_passing_test_is_written_under_output_dir_and_verified(tmp_path):
    repo = _make_repo(tmp_path)
    model = scripted([tests_reply(PASSING)])
    suite = _run(repo, model)

    assert len(suite.test_files) == 1
    test_file = suite.test_files[0]
    assert test_file.path == "tests/calc/test_ops_add.py"
    assert (repo / test_file.path).exists()
    assert test_file.verified
    # The model is told exactly how to import the code under test
    assert "from calc.ops import add" in model.prompts[0]


def test_failing_test_is_repaired_using_failure_output(tmp_path):
    repo = _make_repo(tmp_path)
    model = scripted([tests_reply(FAILING), tests_reply(PASSING)])
    suite = _run(repo, model)

    test_file = suite.test_files[0]
    assert test_file.verified
    assert "== 5" in (repo / test_file.path).read_text()
    assert "assert 5 == 6" in model.prompts[1]  # the repair prompt carries the real failure


def test_bad_import_is_repaired(tmp_path):
    repo = _make_repo(tmp_path)
    model = scripted([
        tests_reply(PASSING, imports=["from calculator import add"]),
        tests_reply(PASSING),
    ])
    suite = _run(repo, model)

    assert suite.test_files[0].verified
    assert "calculator" in model.prompts[1]  # collection error reached the repair prompt


def test_unfixable_test_suspected_code_bug_is_kept_as_xfail(tmp_path):
    repo = _make_repo(tmp_path)
    suite = _run(repo, scripted([tests_reply(FAILING)]), scripted([diagnosis_reply("CODE_BUG")]))

    test_file = suite.test_files[0]
    content = (repo / test_file.path).read_text()
    assert "@pytest.mark.xfail(" in content
    assert "possible bug" in content
    assert test_file.verified  # suite stays green


def test_unfixable_wrong_test_is_dropped(tmp_path):
    repo = _make_repo(tmp_path)
    suite = _run(repo, scripted([tests_reply(FAILING)]), scripted([diagnosis_reply("TEST_WRONG")]))

    assert suite.test_files == []
    assert not (repo / "tests/calc/test_ops_add.py").exists()


def test_src_layout_is_importable(tmp_path):
    repo = _make_repo(tmp_path, src_layout=True)
    suite = _run(repo, scripted([tests_reply(PASSING)]))

    assert suite.test_files[0].path == "tests/calc/test_ops_add.py"
    assert suite.test_files[0].verified


def test_rerun_overwrites_previous_file(tmp_path):
    repo = _make_repo(tmp_path)
    _run(repo, scripted([tests_reply(PASSING)]))
    (repo / "tests/calc/test_ops_add.py").write_text("stale")
    (repo / ".code2test").joinpath("code2test.db").unlink()  # force regeneration

    suite = _run(repo, scripted([tests_reply(PASSING)]))
    assert suite.test_files[0].verified
    assert "stale" not in (repo / "tests/calc/test_ops_add.py").read_text()


@pytest.mark.parametrize(
    "source, component, expected",
    [
        ("/repo/calc/ops.py", {"name": "add"}, "tests/calc/test_ops_add.py"),
        ("src/pkg/mod.py", {"id": "pkg.mod.Foo"}, "tests/pkg/test_mod_foo.py"),
        ("mod.py", None, "tests/test_mod.py"),
    ],
)
def test_generate_test_path(source, component, expected):
    agent = test_agent_mod.TestAgent(model="test", repo_path="/repo", output_dir="tests")
    assert agent._generate_test_path(source, component) == expected


@pytest.mark.parametrize(
    "component, expected",
    [
        ({"name": "add", "relative_path": "calc/ops.py"}, "from calc.ops import add"),
        ({"name": "Foo", "relative_path": "src/pkg/mod.py"}, "from pkg.mod import Foo"),
        ({"name": "Foo", "relative_path": "pkg/__init__.py"}, "from pkg import Foo"),
        ({"name": "x", "relative_path": "my-scripts/run.py"}, None),
    ],
)
def test_import_line_for(component, expected):
    agent = test_agent_mod.TestAgent(model="test", repo_path="/repo")
    assert agent.import_line_for(component) == expected


def test_component_without_source_code_still_generates(tmp_path):
    agent = test_agent_mod.TestAgent(model=scripted([tests_reply(PASSING)]), repo_path=str(tmp_path))
    from code2test.core.models import Intent

    intent = Intent(component_id="calc.ops.add", component_path="calc/ops.py", intent_text="adds", confidence=0.9)
    component = {"id": "calc.ops.add", "name": "add", "relative_path": "calc/ops.py", "source_code": None}
    test_file = asyncio.run(agent.generate_unit_tests(component, intent))
    assert [tc.name for tc in test_file.test_cases] == ["test_add"]
