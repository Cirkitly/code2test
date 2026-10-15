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


INTENT = {"intent_text": "Returns the sum of a and b", "confidence": 0.9, "reasoning": "docstring"}


def scripted(replies: Iterable[dict], diagnosis: str = "TEST_WRONG") -> FunctionModel:
    """
    A model that answers by requested output type: intent and diagnosis requests get
    fixed answers, test generation/repair requests get the next scripted reply
    (the last one repeats).
    """
    queue: List[dict] = list(replies)
    prompts: List[str] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = info.output_tools[0]
        fields = tool.parameters_json_schema.get("properties", {})
        if "intent_text" in fields:
            args = INTENT
        elif "cause" in fields:
            args = diagnosis_reply(diagnosis)
        else:
            prompts.append(str(messages[-1]))
            args = queue.pop(0) if len(queue) > 1 else queue[0]
        return ModelResponse(parts=[ToolCallPart(tool.name, args)])

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


def _run(repo: Path, model: FunctionModel):
    gen = generator_mod.TestGenerator(
        repo_path=str(repo),
        config=GenerationConfig(auto_accept=True, confidence_threshold=0.0, output_dir="tests", model=model),
    )
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
    suite = _run(repo, scripted([tests_reply(FAILING)], diagnosis="CODE_BUG"))

    test_file = suite.test_files[0]
    content = (repo / test_file.path).read_text()
    assert "@pytest.mark.xfail(" in content
    assert "possible bug" in content
    assert test_file.verified  # suite stays green


def test_unfixable_wrong_test_is_dropped(tmp_path):
    repo = _make_repo(tmp_path)
    suite = _run(repo, scripted([tests_reply(FAILING)], diagnosis="TEST_WRONG"))

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


def test_low_confidence_intent_is_refined_by_llm(tmp_path):
    repo = _make_repo(tmp_path)
    gen = generator_mod.TestGenerator(
        repo_path=str(repo),
        config=GenerationConfig(auto_accept=True, confidence_threshold=0.95, model=scripted([tests_reply(PASSING)])),
    )
    intents = asyncio.run(gen._extract_intents_phase(_components(repo)))
    intent = intents["calc.ops.add"]
    assert intent.intent_text == INTENT["intent_text"]
    assert intent.confidence == 0.9


def test_module_imports_are_resolved_to_absolute(tmp_path):
    pkg = tmp_path / "shop"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "cart.py").write_text(
        "import math\nfrom .models import Item\nfrom . import utils\nfrom typing import List\n\ndef total(items):\n    return 0\n"
    )
    agent = test_agent_mod.TestAgent(model="test", repo_path=str(tmp_path))
    component = {"name": "total", "file_path": str(pkg / "cart.py"), "relative_path": "shop/cart.py"}
    assert agent.module_imports_for(component).splitlines() == [
        "import math",
        "from shop.models import Item",
        "from shop import utils",
        "from typing import List",
    ]


def test_unimportable_test_is_never_kept_as_xfail(tmp_path):
    repo = _make_repo(tmp_path)
    # the model keeps importing a name that doesn't exist; diagnosis wrongly blames the code
    bad = tests_reply(PASSING, imports=["from calc.ops import add_numbers as add"])
    suite = _run(repo, scripted([bad], diagnosis="CODE_BUG"))

    assert suite.test_files == []
    assert not (repo / "tests/calc/test_ops_add.py").exists()


def test_escaped_test_code_is_unescaped():
    from code2test.agents.test_agent import clean_code

    escaped = "def test_x():\\n    assert \\\"a\\\" == 'a'\\n"
    assert clean_code(escaped) == "def test_x():\n    assert \"a\" == 'a'\n"
    normal = "def test_x():\n    assert '\\n' == chr(10)\n"
    assert clean_code(normal) == normal


def test_package_init_tests_get_readable_names():
    agent = test_agent_mod.TestAgent(model="test", repo_path="/repo")
    assert agent._generate_test_path("/repo/inflection/__init__.py", {"name": "humanize"}) == "tests/inflection/test_humanize.py"


def test_failures_are_matched_by_defined_function_not_reported_name(tmp_path):
    repo = _make_repo(tmp_path)
    reply = tests_reply(FAILING)
    reply["tests"][0]["name"] = "test_something_else"  # model reports a different name
    suite = _run(repo, scripted([reply], diagnosis="TEST_WRONG"))

    # the failing test is recognised, repaired (same failing code), then dropped
    assert suite.test_files == []
    assert not (repo / "tests/calc/test_ops_add.py").exists()


def test_tests_that_break_each_other_are_dropped_by_the_suite_check(tmp_path):
    from code2test.core.models import TestCase as Case, TestFile as File

    repo = _make_repo(tmp_path)
    (repo / "calc" / "state.py").write_text("ITEMS = []\n")
    polluter = File(
        path="tests/calc/test_a_polluter.py", component_id="a", component_path="calc/state.py",
        imports=["from calc import state"], verified=True,
        test_cases=[Case(name="test_appends", intent_text="", test_code=
                         "def test_appends():\n    state.ITEMS.append(1)\n    assert state.ITEMS\n")],
    )
    victim = File(
        path="tests/calc/test_b_victim.py", component_id="b", component_path="calc/state.py",
        imports=["from calc import state"], verified=True,
        test_cases=[
            Case(name="test_starts_empty", intent_text="", test_code="def test_starts_empty():\n    assert state.ITEMS == []\n"),
            Case(name="test_is_list", intent_text="", test_code="def test_is_list():\n    assert isinstance(state.ITEMS, list)\n"),
        ],
    )
    gen = generator_mod.TestGenerator(repo_path=str(repo), config=GenerationConfig(model="test"))
    for tf in (polluter, victim):
        gen.verifier.write_test_file(tf)
        assert gen.verifier.run_tests(tf).all_passed  # each passes on its own

    kept = asyncio.run(gen._suite_check_phase([polluter, victim]))

    assert [tc.name for tc in victim.test_cases] == ["test_is_list"]
    assert {tf.path for tf in kept} == {polluter.path, victim.path}
    assert gen.verifier.run_pytest([repo / polluter.path, repo / victim.path]).ok


def test_related_api_shows_signatures_of_imported_project_modules(tmp_path):
    pkg = tmp_path / "shop"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "storage.py").write_text(
        "class MemoryStorage:\n    \"\"\"Keeps data in memory.\"\"\"\n"
        "    def __init__(self):\n        self.data = {}\n"
        "    def read(self) -> dict:\n        return self.data\n"
        "    def _secret(self):\n        pass\n"
    )
    (pkg / "db.py").write_text(
        "from .storage import MemoryStorage\n\n"
        "class DB:\n    def __init__(self, storage=MemoryStorage):\n        self.storage = storage()\n\n"
        "def helper(x: int) -> int:\n    return x\n"
    )
    agent = test_agent_mod.TestAgent(model="test", repo_path=str(tmp_path))
    api = agent.related_api_for({"name": "DB", "file_path": str(pkg / "db.py"), "relative_path": "shop/db.py"})

    assert "def helper(x: int) -> int:" in api          # rest of its own module
    assert "class DB" not in api                          # not the component itself
    assert "class MemoryStorage:" in api and '"""Keeps data in memory."""' in api
    assert "def read(self) -> dict: ..." in api
    assert "_secret" not in api and "self.data = {}" not in api  # no private members or bodies


def test_mixed_escaped_code_is_unescaped():
    from code2test.agents.test_agent import clean_code

    mixed = '@pytest.fixture\ndef doc():\n    return {\\"count\\": 5}\\n'
    assert clean_code(mixed) == '@pytest.fixture\ndef doc():\n    return {"count": 5}\n'
