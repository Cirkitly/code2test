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

from code2test.core.models import DiagnosisCause, TestCase, TestFile, TestStatus
from code2test.core.verifier import TestVerifier, test_file_for_classname

logger = logging.getLogger(__name__)

# How much component source the diagnosis agent is shown (see DiagnosisAgent)
DIAGNOSIS_SOURCE_LIMIT = 16000


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
    """Ids of nodes no test can observe a change in: docstrings and type annotations."""
    ids = set()

    def exclude(node: Optional[ast.AST]) -> None:
        if node is not None:
            ids.update(id(n) for n in ast.walk(node))

    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                ids.add(id(body[0].value))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            exclude(node.returns)
            args = node.args
            for arg in args.posonlyargs + args.args + args.kwonlyargs + [a for a in (args.vararg, args.kwarg) if a]:
                exclude(arg.annotation)
        elif isinstance(node, ast.AnnAssign):
            exclude(node.annotation)
    return ids


def _mutation_sites(node: ast.AST, docstrings: set) -> List[Tuple[ast.AST, str]]:
    """(node, kind) pairs inside `node` that can be mutated."""
    sites = []
    for child in ast.walk(node):
        if isinstance(child, ast.Compare) and id(child) not in docstrings:
            for i, op in enumerate(child.ops):
                if type(op) in _SWAP_OPS:
                    sites.append((child, f"cmp:{i}"))
        elif id(child) in docstrings:
            continue
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
            node.value = _perturb_string(old)
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


def _perturb_string(value: str) -> str:
    """A plausible-looking change to a string (no tell-tale markers like "_wrong")."""
    if len(value) > 1:
        return value[:-1]                      # drop the last character
    return value.swapcase() if value.swapcase() != value else value + value


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
                    old = value.value
                    if isinstance(old, int):
                        value.value = old + 1
                    elif isinstance(old, float):
                        value.value = old + 1.5
                    elif isinstance(old, str) and old:
                        value.value = _perturb_string(old)
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
    mutants_killed: int = 0              # by any generated test (standard mutation score)
    mutants_killed_by_own_tests: int = 0  # by the tests generated for the mutated component
    survivors: List[Dict[str, object]] = field(default_factory=list)
    diagnosis_cases: List[DiagnosisCase] = field(default_factory=list)
    diagnosis_error: Optional[str] = None     # set when the model could not be reached
    restored_files: List[str] = field(default_factory=list)  # left mutated by an earlier, killed run

    @property
    def mutation_score(self) -> Optional[float]:
        return self.mutants_killed / self.mutants_total if self.mutants_total else None

    @property
    def own_tests_mutation_score(self) -> Optional[float]:
        return self.mutants_killed_by_own_tests / self.mutants_total if self.mutants_total else None

    @property
    def diagnosis_accuracy(self) -> Optional[float]:
        cases = [c for c in self.diagnosis_cases if c.actual is not None]
        return sum(c.correct for c in cases) / len(cases) if cases else None

    def to_dict(self) -> Dict[str, object]:
        by_label: Dict[str, Dict[str, int]] = {}
        for c in self.diagnosis_cases:
            row = by_label.setdefault(c.expected, {"cases": 0, "correct": 0, "unscored": 0})
            if c.actual is None:
                row["unscored"] += 1
                continue
            row["cases"] += 1
            row["correct"] += int(c.correct)
        return {
            "mutation_score": self.mutation_score,
            "mutants_total": self.mutants_total,
            "mutants_killed": self.mutants_killed,
            "own_tests_mutation_score": self.own_tests_mutation_score,
            "mutants_killed_by_own_tests": self.mutants_killed_by_own_tests,
            "diagnosis_accuracy": self.diagnosis_accuracy,
            "diagnosis_by_expected_cause": by_label,
            "diagnosis_error": self.diagnosis_error,
            "restored_files": self.restored_files,
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
            if path.is_absolute():
                try:
                    path = path.relative_to(self.repo_root)
                except ValueError:
                    logger.warning(f"Skipping {tf.component_id}: {path} is outside {self.repo_root} (repo moved?)")
                    continue
            if not (self.repo_root / path).is_file():
                logger.warning(f"Skipping {tf.component_id}: {path} not found")
                continue
            by_source.setdefault(str(path), []).append(tf)
        return by_source

    @property
    def backup_dir(self) -> Path:
        return self.repo_root / ".code2test" / "benchmark_backup"

    def _remove_empty_backup_dirs(self) -> None:
        if not self.backup_dir.is_dir():
            return
        for directory in sorted((p for p in self.backup_dir.rglob("*") if p.is_dir()), reverse=True):
            if not any(directory.iterdir()):
                directory.rmdir()
        if not any(self.backup_dir.iterdir()):
            self.backup_dir.rmdir()

    def restore_leftovers(self) -> List[str]:
        """Restore source files an earlier, killed run left mutated (from their on-disk backup)."""
        restored = []
        if not self.backup_dir.is_dir():
            return restored
        for backup in sorted(p for p in self.backup_dir.rglob("*") if p.is_file()):
            rel = backup.relative_to(self.backup_dir)
            (self.repo_root / rel).write_bytes(backup.read_bytes())
            backup.unlink()
            restored.append(str(rel))
            logger.warning(f"Restored {rel} from a benchmark backup (an earlier run was interrupted)")
        return restored

    def mutants(self, max_mutants: int) -> List[Mutant]:
        all_mutants: List[Mutant] = []
        for rel_file, files in self._tests_by_source().items():
            names = {tf.component_id.split(".")[-1]: tf.component_id for tf in files}
            all_mutants.extend(generate_mutants(self.repo_root, rel_file, names))
        if len(all_mutants) > max_mutants:
            all_mutants = self.random.sample(all_mutants, max_mutants)
        return sorted(all_mutants, key=lambda m: (m.file, m.line))

    async def run(self, max_mutants: int = 50, max_diagnoses: int = 10) -> BenchmarkResult:
        result = BenchmarkResult(restored_files=self.restore_leftovers())
        # Every mutant runs against the whole generated suite, as in standard mutation
        # testing: a bug in one function is often caught by tests of the functions using it.
        all_paths = sorted({self.repo_root / tf.path for tf in self.test_files})
        own_files: Dict[str, set] = {}
        for tf in self.test_files:
            own_files.setdefault(tf.component_id, set()).add(tf.path)
        code_bug_cases: List[Tuple[TestCase, str, Dict]] = []

        for mutant in self.mutants(max_mutants):
            source_path = self.repo_root / mutant.file
            backup = self.backup_dir / mutant.file
            original = source_path.read_bytes()  # bytes: line endings and encoding come back exactly
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(original)        # survives a killed process; restored on the next run
            try:
                source_path.write_bytes(mutant.source.encode("utf-8"))
                run = self.verifier.run_pytest(all_paths)
            finally:
                source_path.write_bytes(original)
                backup.unlink(missing_ok=True)

            result.mutants_total += 1
            if run.ok or run.returncode == 5:
                result.survivors.append({"file": mutant.file, "line": mutant.line,
                                         "component": mutant.component_id, "mutation": mutant.description})
                continue
            result.mutants_killed += 1

            # Failures in the mutated component's own tests: the per-component score,
            # and the only failures shown to the diagnosis agent (its intent matches)
            mine = own_files.get(mutant.component_id, set())
            failed = [c for c in run.cases if c.outcome == "failed"
                      and test_file_for_classname(self.repo_root, c.classname) in mine]
            if failed:
                result.mutants_killed_by_own_tests += 1
                case = failed[0]
                test_case = self._find_test_case(mutant.component_id, case.name)
                source, offset = _component_source(mutant.source, mutant.component_id, mutant.line)
                # Only cases where the diagnosis agent is shown the mutated line are fair
                if test_case is not None and offset <= DIAGNOSIS_SOURCE_LIMIT - 500:
                    component = dict(self.components.get(mutant.component_id, {}))
                    component["source_code"] = source
                    code_bug_cases.append((test_case, case.message, component))

        self._remove_empty_backup_dirs()

        if len(code_bug_cases) > max_diagnoses:
            code_bug_cases = self.random.sample(code_bug_cases, max_diagnoses)

        if self.diagnosis_agent is not None:
            from code2test.agents.errors import ModelAccessError
            try:
                for test_case, message, component in code_bug_cases:
                    result.diagnosis_cases.append(
                        await self._diagnose(test_case, message, component, DiagnosisCause.CODE_BUG)
                    )
                for test_case, message, component in await self._wrong_test_cases(max_diagnoses):
                    result.diagnosis_cases.append(
                        await self._diagnose(test_case, message, component, DiagnosisCause.TEST_WRONG)
                    )
            except ModelAccessError as e:
                # Keep the mutation results, which needed no model
                result.diagnosis_error = str(e)
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
            # The whole file, with only this test's expected value changed: helpers and
            # fixtures defined by sibling tests stay available.
            target = TestCase(name=tc.name, intent_text=tc.intent_text, test_code=broken)
            probe = TestFile(
                path=str(Path(tf.path).with_name(f"_c2t_probe_{Path(tf.path).name}")),
                component_id=tf.component_id, component_path=tf.component_path,
                imports=tf.imports, fixtures=tf.fixtures,
                test_cases=[target if other is tc else other.model_copy() for other in tf.test_cases],
            )
            try:
                verification = self.verifier.run_tests(probe)
            finally:
                (self.repo_root / probe.path).unlink(missing_ok=True)
            message = target.failure_message or ""
            # Only a failure of the changed assertion is a TEST_WRONG case with a known cause
            if verification.collection_error or target.status != TestStatus.FAILED or not _is_assertion_failure(message):
                continue
            cases.append((target, message, self.components.get(tf.component_id, {})))
        return cases

    async def _diagnose(self, test_case: TestCase, message: str, component: Dict,
                        expected: DiagnosisCause) -> DiagnosisCase:
        case = DiagnosisCase(test=test_case.name, expected=expected.value)
        intent = self.intents.get(component.get("id", ""))
        if intent is None:
            return case
        diagnosis = await self.diagnosis_agent.diagnose_failure(test_case, message, component, intent)
        case.explanation = diagnosis.explanation[:300]
        if diagnosis.explanation.startswith("Unable to diagnose"):
            return case  # the model call failed: not an answer, leave it unscored
        case.actual = diagnosis.cause.value
        return case


def _is_assertion_failure(message: str) -> bool:
    """True when pytest's failure message is a failed assertion, not some other error."""
    lines = [l.strip() for l in (message or "").splitlines() if l.strip()]
    return bool(lines) and (lines[0].startswith("assert ") or lines[0].startswith("AssertionError"))


def _component_source(module_source: str, component_id: str, line: int = 0) -> Tuple[str, int]:
    """The component's source, and the character offset of `line` within it."""
    name = component_id.split(".")[-1]
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        return module_source, 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            segment = ast.get_source_segment(module_source, node) or module_source
            before = segment.splitlines()[: max(0, line - node.lineno)]
            return segment, sum(len(l) + 1 for l in before)
    return module_source, 0
