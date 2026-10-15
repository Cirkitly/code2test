"""
Report command for Code2Test CLI.
"""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from code2test.cli.display import DisplayManager

console = Console()


def _pct(value) -> str:
    return "n/a" if value is None else f"{100 * value:.0f}%"


@click.command("report")
@click.argument("type", type=click.Choice(["summary", "coverage"]), default="summary")
@click.option(
    "--format",
    type=click.Choice(["text", "html", "json"]),
    default="text",
    help="Output format for the coverage report",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="File for html/json output (default: tests/reports/coverage.html or .json)",
)
def report_command(type: str, format: str, output: Optional[str]) -> None:
    """
    Report on the generated tests.

    Run it from the project root after 'code2test test'.

    \b
    summary   stored intents by confidence
    coverage  behavioral coverage and diagnostic accuracy: the behaviors each
              component's passing tests check and, after 'code2test benchmark',
              the share of injected bugs they catch and how often the diagnosis
              names the right cause

    \b
    Examples:
        code2test report summary
        code2test report coverage
        code2test report coverage --format html
    """
    display = DisplayManager()

    from code2test.storage import IntentDatabase, TestRegistry

    repo_root = Path.cwd()
    db_path = repo_root / ".code2test" / "code2test.db"
    if not db_path.exists():
        display.error("No database found. Run 'code2test test' first.")
        return

    db = IntentDatabase(str(db_path))

    if type == "summary":
        intents = db.get_all_intents()
        table = Table(title="Code2Test Summary Report")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Intents Extracted", str(len(intents)))
        table.add_row(
            "High Confidence (>80%)", str(len([i for i in intents if i.confidence >= 0.8]))
        )
        table.add_row(
            "Medium Confidence (>50%)", str(len([i for i in intents if 0.5 <= i.confidence < 0.8]))
        )
        table.add_row("Low Confidence (<50%)", str(len([i for i in intents if i.confidence < 0.5])))
        console.print(table)
        return

    from code2test.core.quality import quality_report

    quality = quality_report(
        repo_root, TestRegistry(str(db_path)).get_all_tests(), db.get_all_intents_dict()
    )

    if format in ("html", "json"):
        from code2test.reporting import HTMLReportGenerator, JSONReportGenerator

        path = Path(output) if output else repo_root / "tests" / "reports" / f"coverage.{format}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if format == "html":
            HTMLReportGenerator().generate_quality_report(quality, str(path))
        else:
            JSONReportGenerator().generate_quality_report(quality, str(path))
        display.success(f"Coverage report written to {path}")
        return

    table = Table(title="Behavioral coverage")
    table.add_column("Component", style="cyan")
    table.add_column("Passing tests", justify="right")
    table.add_column("Behaviors tested", justify="right")
    table.add_column("Mutants killed", justify="right")
    for c in quality["components"]:
        killed = (
            f"{c['mutants_killed']}/{c['mutants']} ({_pct(c['mutation_score'])})"
            if c["mutants"]
            else "n/a"
        )
        table.add_row(
            c["component"], str(c["tests_passing"]), str(len(c["behaviors_tested"])), killed
        )
    console.print(table)

    summary, bench = quality["summary"], quality["benchmark"]
    console.print(
        f"Behaviors tested: {summary['behaviors_tested']} across "
        f"{summary['components_with_passing_tests']}/{summary['components']} components"
    )
    if not bench["available"]:
        display.info(
            "Run 'code2test benchmark' to measure the mutation score and the diagnostic accuracy."
        )
        return
    console.print(
        f"Mutation score: {_pct(bench['mutation_score'])} "
        f"({bench['mutants_killed']}/{bench['mutants_total']} injected bugs caught)"
    )
    console.print(f"Diagnostic accuracy: {_pct(bench['diagnosis_accuracy'])}")
    for cause, row in (bench.get("diagnosis_by_expected_cause") or {}).items():
        console.print(f"  {cause}: {row.get('correct', 0)}/{row.get('cases', 0)}")
    console.print(f"From the benchmark run of {bench.get('created_at') or 'an unknown date'}.")
    if bench["stale"]:
        display.warning(
            "That benchmark predates the last 'code2test test' run; run 'code2test benchmark' again."
        )
