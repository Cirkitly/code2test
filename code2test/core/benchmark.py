"""
Code2Test benchmark: how good are the tests code2test generated?

Two measurements on a project that already has generated tests:

1. Mutation score: small bugs (mutants) are injected into the tested functions one
   at a time; a mutant is "killed" when the generated tests for it fail. A high
   score means the tests check behaviour rather than just passing.
2. Diagnosis accuracy: the diagnosis agent is shown failures whose cause is known:
   tests failing because the code was mutated (expected CODE_BUG) and tests whose
   expected value was deliberately broken (expected TEST_WRONG).

The source tree is always restored after each mutant, even on errors.
"""

import ast
import logging
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from code2test.core.models import DiagnosisCause, TestCase, TestFile
from code2test.core.verifier import TestVerifier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mutants
# ---------------------------------------------------------------------------

_SWAP_OPS = {
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt,
    ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
    ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult,
    ast.Div: ast.Mult, ast.Mod: ast.FloorDiv,
    ast.And: ast.Or, ast.Or: ast.And,
}


@dataclass
class Mutant:
    file: str           # source file, relative to the repo root
    component_id: str   # top-level function/class the mutant is in
    line: int
    description: str
    source: str         # full mutated source of the file


def _docstring_nodes(tree: ast.AST) -> set:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _mutation_sites(node: ast.AST, docstrings: set) -> List[Tuple[ast.AST, str]]:
    """(node, kind) pairs inside `node` that can be mutated."""
    sites = []
    for child in ast.walk(node):
        if isinstance(child, ast.Compare):
            for i, op in enumerate(child.ops):
                if type(op) in _SWAP_OPS:
                    sites.append((child, f"cmp:{i}"))
        elif isinstance(child, (ast.BinOp, ast.BoolOp)) and type(child.op) in _SWAP_OPS:
            sites.append((child, "op"))
        elif isinstance(child, ast.Constant) and id(child) not in docstrings:
            if isinstance(child.value, bool) or (isinstance(child.value, int) and not isinstance(child.value, bool)):
                sites.append((child, "const"))
            elif isinstance(child.value, str) and child.value:
                sites.append((child, "const"))
        elif isinstance(child, ast.Return) and child.value is not None and not (
            isinstance(child.value, ast.Constant) and child.value.value is None
        ):
            sites.append((child, "return"))
    return sites


def _apply(node: ast.AST, kind: str) -> str:
    """Mutate `node` in place and describe the change."""
    if kind.startswith("cmp:"):
        i = int(kind.split(":")[1])
        old = node.ops[i]
        node.ops[i] = _SWAP_OPS[type(old)]()
        return f"{type(old).__name__} -> {type(node.ops[i]).__name__}"
    if kind == "op":
        old = node.op
        node.op = _SWAP_OPS[type(old)]()
        return f"{type(old).__name__} -> {type(node.op).__name__}"
    if kind == "const":
        old = node.value
        if isinstance(old, bool):
            node.value = not old
        elif isinstance(old, int):
            node.value = old + 1
        else:
            node.value = old + "_mutated"
        return f"{old!r} -> {node.value!r}"
    if kind == "return":
        node.value = ast.Constant(value=None)
        return "return value -> None"
    raise ValueError(kind)


def generate_mutants(repo_root: Path, rel_file: str, component_names: Dict[str, str]) -> List[Mutant]:
    """
    All single-site mutants of the top-level functions/classes named in
    `component_names` (name -> component id) within one source file.
    """
    source = (repo_root / rel_file).read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    mutants = []
    for top_index, top in enumerate(tree.body):
        if not isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if top.name not in component_names:
            continue
        count = len(_mutation_sites(top, _docstring_nodes(tree)))
        for site_index in range(count):
            # Re-parse for every mutant so each one changes exactly one site
            fresh = ast.parse(source)
            target = fresh.body[top_index]
            node, kind = _mutation_sites(target, _docstring_nodes(fresh))[site_index]
            description = _apply(node, kind)
            ast.fix_missing_locations(fresh)
            try:
                mutated = ast.unparse(fresh)
            except Exception:
                continue
            mutants.append(Mutant(
                file=rel_file,
                component_id=component_names[top.name],
                line=getattr(node, "lineno", top.lineno),
                description=description,
                source=mutated,
            ))
    return mutants


# ---------------------------------------------------------------------------
# Wrong tests (for TEST_WRONG diagnosis cases)
# ---------------------------------------------------------------------------

def break_expected_value(test_code: str) -> Optional[str]:
    """
    Change the expected value of the first `assert x == <literal>` in a test, so
    the test is wrong while the code is right. None if there is no such assert.
    """
    try:
        tree = ast.parse(test_code)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)):
            for side in ("comparators", "left"):
                value = node.test.comparators[0] if side == "comparators" else node.test.left
                if isinstance(value, ast.Constant) and not isinstance(value.value, bool):
                    if isinstance(value.value, int):
                        value.value += 1
                    elif isinstance(value.value, float):
                        value.value += 1.5
                    elif isinstance(value.value, str):
                        value.value += "_wrong"
                    else:
                        continue
                    return ast.unparse(tree)
    return None


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisCase:
    test: str
    expected: str
    actual: Optional[str] = None
    explanation: str = ""

    @property
    def correct(self) -> bool:
        return self.actual == self.expected


@dataclass
class BenchmarkResult:
    mutants_total: int = 0
    mutants_killed: int = 0
    survivors: List[Dict[str, object]] = field(default_factory=list)
    diagnosis_cases: List[DiagnosisCase] = field(default_factory=list)

    @property
    def mutation_score(self) -> Optional[float]:
        return self.mutants_killed / self.mutants_total if self.mutants_total else None

    @property
    def diagnosis_accuracy(self) -> Optional[float]:
        cases = [c for c in self.diagnosis_cases if c.actual is not None]
        return sum(c.correct for c in cases) / len(cases) if cases else None

    def to_dict(self) -> Dict[str, object]:
        by_label: Dict[str, Dict[str, int]] = {}
        for c in self.diagnosis_cases:
            row = by_label.setdefault(c.expected, {"cases": 0, "correct": 0})
            row["cases"] += 1
            row["correct"] += int(c.correct)
        return {
            "mutation_score": self.mutation_score,
            "mutants_total": self.mutants_total,
            "mutants_killed": self.mutants_killed,
            "diagnosis_accuracy": self.diagnosis_accuracy,
            "diagnosis_by_expected_cause": by_label,
            "survivors": self.survivors,
            "diagnosis_cases": [{**asdict(c), "correct": c.correct} for c in self.diagnosis_cases],
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class Benchmark:
    """Runs mutation testing and diagnosis evaluation for generated tests."""

    def __init__(self, repo_root: Path, test_files: List[TestFile], intents: Dict, components: Dict[str, Dict],
                 diagnosis_agent=None, timeout: int = 120, seed: int = 0):
        self.repo_root = Path(repo_root)
        self.test_files = test_files
        self.intents = intents
        self.components = components
        self.diagnosis_agent = diagnosis_agent
        self.verifier = TestVerifier(str(repo_root), timeout=timeout)
        self.random = random.Random(seed)

    def _tests_by_source(self) -> Dict[str, List[TestFile]]:
        by_source: Dict[str, List[TestFile]] = {}
        for tf in self.test_files:
            path = Path(tf.component_path)
            rel = str(path.relative_to(self.repo_root)) if path.is_absolute() else str(path)
            by_source.setdefault(rel, []).append(tf)
        return by_source

    def mutants(self, max_mutants: int) -> List[Mutant]:
        all_mutants: List[Mutant] = []
        for rel_file, files in self._tests_by_source().items():
            names = {tf.component_id.split(".")[-1]: tf.component_id for tf in files}
            all_mutants.extend(generate_mutants(self.repo_root, rel_file, names))
        if len(all_mutants) > max_mutants:
            all_mutants = self.random.sample(all_mutants, max_mutants)
        return sorted(all_mutants, key=lambda m: (m.file, m.line))

    async def run(self, max_mutants: int = 50, max_diagnoses: int = 10) -> BenchmarkResult:
        result = BenchmarkResult()
        test_paths = {tf.component_id: [self.repo_root / tf.path] for tf in self.test_files}
        code_bug_cases: List[Tuple[TestCase, str, Dict]] = []

        for mutant in self.mutants(max_mutants):
            source_path = self.repo_root / mutant.file
            original = source_path.read_text()
            try:
                source_path.write_text(mutant.source)
                run = self.verifier.run_pytest(test_paths.get(mutant.component_id, []))
            finally:
                source_path.write_text(original)

            result.mutants_total += 1
            if run.ok or run.returncode == 5:
                result.survivors.append({"file": mutant.file, "line": mutant.line,
                                         "component": mutant.component_id, "mutation": mutant.description})
                continue
            result.mutants_killed += 1

            failed = [c for c in run.cases if c.outcome == "failed"]
            if failed and len(code_bug_cases) < max_diagnoses:
                case = failed[0]
                test_case = self._find_test_case(mutant.component_id, case.name)
                if test_case is not None:
                    component = dict(self.components.get(mutant.component_id, {}))
                    component["source_code"] = _component_source(mutant.source, mutant.component_id)
                    code_bug_cases.append((test_case, case.message, component))

        if self.diagnosis_agent is not None:
            for test_case, message, component in code_bug_cases:
                result.diagnosis_cases.append(
                    await self._diagnose(test_case, message, component, DiagnosisCause.CODE_BUG)
                )
            for test_case, message, component in await self._wrong_test_cases(max_diagnoses):
                result.diagnosis_cases.append(
                    await self._diagnose(test_case, message, component, DiagnosisCause.TEST_WRONG)
                )
        return result

    def _find_test_case(self, component_id: str, name: str) -> Optional[TestCase]:
        for tf in self.test_files:
            if tf.component_id != component_id:
                continue
            for tc in tf.test_cases:
                if tc.name == name or f"def {name}(" in tc.test_code:
                    return tc
        return None

    async def _wrong_test_cases(self, limit: int) -> List[Tuple[TestCase, str, Dict]]:
        """Passing tests with a deliberately wrong expected value, run to get their failure."""
        candidates = [(tf, tc) for tf in self.test_files for tc in tf.test_cases
                      if not tc.diagnosis and "xfail" not in tc.test_code]
        self.random.shuffle(candidates)
        cases = []
        for tf, tc in candidates:
            if len(cases) >= limit:
                break
            broken = break_expected_value(tc.test_code)
            if broken is None:
                continue
            probe = TestFile(
                path=str(Path(tf.path).with_name(f"_c2t_probe_{Path(tf.path).name}")),
                component_id=tf.component_id, component_path=tf.component_path,
                imports=tf.imports, fixtures=tf.fixtures,
                test_cases=[TestCase(name=tc.name, intent_text=tc.intent_text, test_code=broken)],
            )
            try:
                verification = self.verifier.run_tests(probe)
            finally:
                (self.repo_root / probe.path).unlink(missing_ok=True)
            if verification.all_passed or verification.collection_error:
                continue
            failing = probe.test_cases[0]
            cases.append((failing, failing.failure_message or "", self.components.get(tf.component_id, {})))
        return cases

    async def _diagnose(self, test_case: TestCase, message: str, component: Dict,
                        expected: DiagnosisCause) -> DiagnosisCase:
        case = DiagnosisCase(test=test_case.name, expected=expected.value)
        intent = self.intents.get(component.get("id", ""))
        if intent is None:
            return case
        diagnosis = await self.diagnosis_agent.diagnose_failure(test_case, message, component, intent)
        case.actual = diagnosis.cause.value
        case.explanation = diagnosis.explanation[:300]
        return case


def _component_source(module_source: str, component_id: str) -> str:
    name = component_id.split(".")[-1]
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        return module_source
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return ast.get_source_segment(module_source, node) or module_source
    return module_source
