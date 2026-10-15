"""
Code2Test run metrics.

Measures a generation run against the MVP success criteria in docs/proposal.md:

- acceptance rate: share of components that end up with at least one kept test
- first-run pass rate: share of generated tests that pass before any repair
- what the repair loop did: tests repaired, kept as xfail, dropped
"""

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileMetrics:
    """What happened to one generated test file."""

    component_id: str
    path: str
    generated: int = 0          # tests the model wrote
    first_run_passed: int = 0   # tests passing before any repair
    repair_rounds: int = 0      # repair calls made for this file
    kept: int = 0               # tests in the file that was written
    xfail: int = 0              # kept tests marked xfail (suspected code bug)
    removed_reason: Optional[str] = None  # set when the whole file was discarded

    @property
    def dropped(self) -> int:
        return self.generated - self.kept


@dataclass
class RunMetrics:
    """Metrics for one `code2test test` run."""

    components: int = 0
    files: Dict[str, FileMetrics] = field(default_factory=dict)
    diagnoses: Counter = field(default_factory=Counter)  # cause -> count
    llm_failures: int = 0       # components whose generation call failed

    def file(self, component_id: str, path: str) -> FileMetrics:
        if path not in self.files:
            self.files[path] = FileMetrics(component_id=component_id, path=path)
        return self.files[path]

    # Totals -------------------------------------------------------------

    @property
    def generated(self) -> int:
        return sum(f.generated for f in self.files.values())

    @property
    def first_run_passed(self) -> int:
        return sum(f.first_run_passed for f in self.files.values())

    @property
    def kept(self) -> int:
        return sum(f.kept for f in self.files.values())

    @property
    def xfail(self) -> int:
        return sum(f.xfail for f in self.files.values())

    @property
    def components_with_tests(self) -> int:
        return len({f.component_id for f in self.files.values() if f.kept > f.xfail})

    @property
    def acceptance_rate(self) -> float:
        return self.components_with_tests / self.components if self.components else 0.0

    @property
    def first_run_pass_rate(self) -> float:
        return self.first_run_passed / self.generated if self.generated else 0.0

    @property
    def keep_rate(self) -> float:
        return self.kept / self.generated if self.generated else 0.0

    def summary(self) -> Dict[str, object]:
        return {
            "components": self.components,
            "components_with_tests": self.components_with_tests,
            "acceptance_rate": round(self.acceptance_rate, 3),
            "tests_generated": self.generated,
            "first_run_passed": self.first_run_passed,
            "first_run_pass_rate": round(self.first_run_pass_rate, 3),
            "tests_kept": self.kept,
            "tests_xfail": self.xfail,
            "tests_dropped": self.generated - self.kept,
            "files_removed": sum(1 for f in self.files.values() if f.removed_reason),
            "repair_rounds": sum(f.repair_rounds for f in self.files.values()),
            "diagnoses": dict(self.diagnoses),
            "llm_failures": self.llm_failures,
        }

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary": self.summary(),
            "files": [
                {**asdict(f), "dropped": f.dropped}
                for f in sorted(self.files.values(), key=lambda f: f.path)
            ],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))


# MVP targets from docs/proposal.md section 7.3
TARGETS = {
    "acceptance_rate": 0.70,
    "first_run_pass_rate": 0.80,
    "diagnosis_accuracy": 0.75,
}


def target_rows(values: Dict[str, Optional[float]]) -> List[tuple]:
    """(metric, value, target, met) rows for the metrics that have a target."""
    rows = []
    for name, target in TARGETS.items():
        value = values.get(name)
        rows.append((name, value, target, None if value is None else value >= target))
    return rows
