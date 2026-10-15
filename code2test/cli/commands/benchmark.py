"""
Benchmark command: measure the quality of the tests code2test generated.
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from code2test.cli.display import DisplayManager

console = Console()


@click.command("benchmark")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--mutants", type=int, default=50, show_default=True, help="Maximum number of mutants to run")
@click.option("--diagnoses", type=int, default=10, show_default=True,
              help="Diagnosis cases per expected cause (0 to skip the LLM part)")
@click.option("--timeout", type=int, default=120, show_default=True, help="pytest timeout per run, in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def benchmark_command(path: str, mutants: int, diagnoses: int, timeout: int, verbose: bool) -> None:
    """
    Measure how good the generated tests are.

    Run after 'code2test test'. Reports the mutation score (share of injected
    bugs the generated tests catch) and the diagnosis accuracy (how often the
    diagnosis agent names the right cause of a failure whose cause is known),
    next to the generation metrics of the last run and the MVP targets.

    \b
    Examples:
        code2test benchmark .
        code2test benchmark --mutants 100 --diagnoses 20 .
    """
    from code2test.cli.commands.test import find_repo_root
    from code2test.cli.commands.verify import load_component
    from code2test.core.benchmark import Benchmark
    from code2test.core.metrics import target_rows
    from code2test.storage import IntentDatabase, TestRegistry

    display = DisplayManager(quiet=not verbose)
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)

    repo_root = find_repo_root(Path(path).resolve())
    db_path = repo_root / ".code2test" / "code2test.db"
    if not db_path.exists():
        display.error("No code2test data found. Run 'code2test test' first.")
        sys.exit(1)

    registry = TestRegistry(str(db_path))
    test_files = [tf for tf in registry.get_all_tests() if (repo_root / tf.path).exists()]
    if not test_files:
        display.error("No generated test files found. Run 'code2test test' first.")
        sys.exit(1)

    # Restore anything an interrupted earlier run left mutated before trusting the baseline
    restored = Benchmark(repo_root, test_files, {}, {}).restore_leftovers()
    for path in restored:
        display.warning(f"Restored {path}: an earlier benchmark run was interrupted while it was mutated")

    baseline = Benchmark(repo_root, test_files, {}, {}, timeout=timeout).verifier.run_pytest(
        [repo_root / tf.path for tf in test_files]
    )
    if not baseline.ok:
        display.error("The generated tests don't all pass yet. Run 'code2test verify --fix' first.")
        sys.exit(1)

    intents = IntentDatabase(str(db_path)).get_all_intents_dict()
    components = {}
    for tf in test_files:
        component = load_component(repo_root, tf.component_id, tf.component_path)
        if component:
            components[tf.component_id] = component

    diagnosis_agent = None
    if diagnoses > 0:
        from code2test.agents.diagnosis_agent import DiagnosisAgent
        from code2test.cli.utils.model import resolve_model

        diagnosis_agent = DiagnosisAgent(model=resolve_model(display))

    bench = Benchmark(repo_root, test_files, intents, components, diagnosis_agent=diagnosis_agent, timeout=timeout)
    console.print(f"Running up to {mutants} mutants against {len(test_files)} generated test files...")
    # A terminated run (CI cancel, closed terminal) must still restore the mutated source:
    # turn SIGTERM/SIGHUP into KeyboardInterrupt so the restore in Benchmark.run executes.
    def _interrupt(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")

    for sig in (signal.SIGTERM, getattr(signal, "SIGHUP", None)):
        if sig is not None:
            signal.signal(sig, _interrupt)
    result = asyncio.run(bench.run(max_mutants=mutants, max_diagnoses=diagnoses))
    if result.diagnosis_error:
        display.warning(f"Diagnosis skipped, the model could not be reached: {result.diagnosis_error}")

    metrics_path = repo_root / ".code2test" / "metrics.json"
    generation = json.loads(metrics_path.read_text())["summary"] if metrics_path.exists() else {}

    table = Table(title="Benchmark")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    def pct(value) -> str:
        return "n/a" if value is None else f"{value:.0%}"

    if generation:
        table.add_row("Components with tests (last run)",
                      f"{generation['components_with_tests']}/{generation['components']} ({pct(generation['acceptance_rate'])})")
        table.add_row("Tests passing on first run (last run)",
                      f"{generation['first_run_passed']}/{generation['tests_generated']} ({pct(generation['first_run_pass_rate'])})")
    if result.mutation_score is not None:
        table.add_row("Mutants killed (whole suite)", f"{result.mutants_killed}/{result.mutants_total} ({result.mutation_score:.0%})")
        table.add_row("  by the mutated component's own tests",
                      f"{result.mutants_killed_by_own_tests}/{result.mutants_total} ({result.own_tests_mutation_score:.0%})")
    scored = [c for c in result.diagnosis_cases if c.actual is not None]
    if scored:
        table.add_row("Diagnoses correct", f"{sum(c.correct for c in scored)}/{len(scored)} ({result.diagnosis_accuracy:.0%})")
        for cause in ("CODE_BUG", "TEST_WRONG"):
            subset = [c for c in scored if c.expected == cause]
            if subset:
                table.add_row(f"  when the cause is {cause}", f"{sum(c.correct for c in subset)}/{len(subset)}")
    console.print(table)

    for name, value, target, met in target_rows({
        "acceptance_rate": generation.get("acceptance_rate"),
        "first_run_pass_rate": generation.get("first_run_pass_rate"),
        "diagnosis_accuracy": result.diagnosis_accuracy,
    }):
        if value is None:
            continue
        mark = "[green]✓[/green]" if met else "[yellow]✗[/yellow]"
        console.print(f"{mark} {name.replace('_', ' ')}: {value:.0%} (MVP target {target:.0%})")

    if result.survivors and verbose:
        console.print("\nMutants the tests did not catch:")
        for s in result.survivors[:20]:
            console.print(f"  {s['file']}:{s['line']} {s['component']}: {s['mutation']}", markup=False)

    out = repo_root / ".code2test" / "benchmark.json"
    out.write_text(json.dumps({"generation": generation, **result.to_dict()}, indent=2))
    display.success(f"Saved {out}")
