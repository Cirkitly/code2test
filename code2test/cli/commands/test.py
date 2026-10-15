"""
Test generation command for Code2Test CLI.
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

import click
from click.core import ParameterSource
from rich.console import Console

from code2test.cli.display import DisplayManager
from code2test.cli.interactive import run_interactive_generation
from code2test.cli.utils.model import resolve_model
from code2test.cli.utils.project_config import (
    PROJECT_DEFAULTS,
    load_project_settings,
    project_config_path,
)
from code2test.core import TestGenerator, GenerationConfig, TestFramework
from code2test.src.be.dependency_analyzer import DependencyGraphBuilder
from code2test.src.config import Config

logger = logging.getLogger(__name__)
console = Console()


@click.command("test")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option(
    "--auto",
    is_flag=True,
    default=False,
    help="Auto-accept high-confidence tests without prompting",
)
@click.option(
    "--confidence",
    type=float,
    default=PROJECT_DEFAULTS["confidence_threshold"],
    show_default=True,
    help="Intent confidence needed to generate tests in --auto mode (0.0-1.0); "
    "overrides .code2test/config.json",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be generated without writing files",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=PROJECT_DEFAULTS["output_dir"],
    show_default=True,
    help="Directory for generated tests, relative to the project root; "
    "overrides .code2test/config.json",
)
@click.option(
    "--include", type=str, default=None, help="Glob pattern for files to include (e.g., '*.py')"
)
@click.option(
    "--exclude",
    type=str,
    multiple=True,
    help="Glob pattern of files to leave out of the analysis (repeatable); "
    "added to the built-in exclusions and those in .code2test/config.json",
)
@click.option(
    "--exit-code/--no-exit-code",
    default=False,
    help="Return non-zero exit code if tests fail or verification fails",
)
@click.option(
    "--report",
    type=click.Choice(["none", "html", "json", "all"]),
    default="none",
    help="Generate reports after test generation",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging")
@click.pass_context
def test_command(
    ctx: click.Context,
    path: str,
    auto: bool,
    confidence: float,
    dry_run: bool,
    output_dir: str,
    include: Optional[str],
    exclude: Tuple[str, ...],
    exit_code: bool,
    report: str,
    verbose: bool,
) -> None:
    """
    Generate tests for a code repository or module.

    Analyzes the code using intent-first analysis and generates comprehensive
    test suites with human-in-the-loop verification.

    \b
    Examples:
        code2test test src/auth/          # Generate tests for auth module
        code2test test --auto .           # Auto-generate for entire repo
        code2test test --dry-run src/     # Preview without writing
        code2test test --confidence 0.8   # Only accept high-confidence
    """
    display = DisplayManager(quiet=not verbose)

    # Setup logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    target_path = Path(path).resolve()
    repo_path = find_repo_root(target_path)

    # Project settings from `code2test init` are defaults; options on the command line win
    settings = load_project_settings(repo_path)
    if ctx.get_parameter_source("confidence") == ParameterSource.DEFAULT:
        confidence = settings.get("confidence_threshold", confidence)
    if ctx.get_parameter_source("output_dir") == ParameterSource.DEFAULT:
        output_dir = settings.get("output_dir", output_dir)
    if settings:
        display.info(f"Using project settings from {project_config_path(repo_path)}")

    # Validate confidence
    if not 0.0 <= confidence <= 1.0:
        display.error("Confidence must be between 0.0 and 1.0")
        sys.exit(1)

    main_model = resolve_model(display)
    display.info(f"Using model: {main_model}")
    display.info(f"Analyzing: {target_path}")

    try:
        # Create configuration
        config = GenerationConfig(
            confidence_threshold=confidence,
            auto_accept=auto,
            dry_run=dry_run,
            output_dir=output_dir,
            framework=TestFramework.PYTEST,
            model=main_model,
        )

        # Build include/exclude patterns
        include_patterns = [include] if include else None

        # More specific default exclude patterns to avoid excluding the repo itself if it has "test" in the name
        default_excludes = [
            "tests",
            "test",
            "*_test.py",
            "test_*.py",
            "*__pycache__*",
            "*.pyc",
            ".git",
            ".tox",
            ".env",
            "venv",
        ]
        # Never analyze the generated tests themselves, wherever they are written
        exclude_patterns = (
            default_excludes
            + _relative_dir_patterns(output_dir, repo_path)
            + settings.get("exclude_patterns", [])
            + list(exclude)
        )

        # Analyze codebase
        display.info("Parsing codebase...")

        # Use the existing dependency analyzer
        # Use the existing dependency analyzer
        # We need to construct Config correctly as it requires many fields
        # and patterns go into agent_instructions
        agent_instructions = {
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
        }

        repo_config = Config(
            repo_path=str(repo_path),
            output_dir=output_dir,
            dependency_graph_dir=str(repo_path / ".code2test" / "dependency_graphs"),
            docs_dir=str(repo_path / ".code2test" / "docs"),
            max_depth=2,
            llm_base_url="",  # Not used for static analysis
            llm_api_key="",
            main_model="",
            cluster_model="",
            agent_instructions=agent_instructions,
        )

        builder = DependencyGraphBuilder(repo_config)
        components, leaf_nodes = builder.build_dependency_graph()

        if not components:
            display.warning("No components found to analyze")
            sys.exit(0)

        display.success(f"Found {len(components)} components")

        # Convert Node objects to dictionaries for compatibility
        # and map 'depends_on' to 'dependencies'
        components_dict = {}
        for k, v in components.items():
            if hasattr(v, "model_dump"):
                data = v.model_dump()
            else:
                data = v.dict()

            # Map depends_on to dependencies
            if "depends_on" in data:
                data["dependencies"] = list(data["depends_on"])
            else:
                data["dependencies"] = []

            components_dict[k] = data

        # Test generation and verification currently target Python (pytest) only
        # Only generate for the requested file/directory (the whole repo is analyzed for context)
        components = {
            k: v
            for k, v in components_dict.items()
            if str(v.get("file_path", "")).endswith(".py")
            and _is_within(v.get("file_path", ""), repo_path, target_path)
        }
        skipped_other = len(components_dict) - len(components)
        if skipped_other:
            display.warning(
                f"Skipping {skipped_other} non-Python components (only Python test generation is supported)"
            )
        if not components:
            display.warning("No Python components found to test")
            sys.exit(0)

        # Create generator
        generator = TestGenerator(
            repo_path=str(repo_path),
            config=config,
        )

        if auto:
            # Non-interactive batch mode
            display.info("Running in auto mode...")

            async def run_batch():
                suite = await generator.generate_tests_for_module(str(repo_path), components)
                return suite

            suite = asyncio.run(run_batch())

            if not dry_run:
                show_run_metrics(generator.metrics)
            else:
                display.show_summary_table(generator.get_stats())

            if not dry_run:
                display.success(
                    f"Generated {suite.total_tests} tests in {len(suite.test_files)} files"
                )

                # Handle reporting
                if report != "none":
                    display.info(f"Generating {report} report...")
                    try:
                        from code2test.core.quality import quality_report
                        from code2test.reporting import HTMLReportGenerator, JSONReportGenerator

                        report_dir = repo_path / output_dir / "reports"
                        report_dir.mkdir(parents=True, exist_ok=True)
                        intents = generator.intent_db.get_all_intents_dict()
                        quality = quality_report(
                            repo_path, generator.test_registry.get_all_tests(), intents
                        )

                        if report in ["html", "all"]:
                            html_path = report_dir / "report.html"
                            html_gen = HTMLReportGenerator()
                            html_gen.generate_report(
                                suite, intents, str(html_path), quality=quality
                            )
                            display.success(f"HTML report generated: {html_path}")

                        if report in ["json", "all"]:
                            json_path = report_dir / "report.json"
                            json_gen = JSONReportGenerator()
                            json_gen.generate_report(
                                suite, intents, str(json_path), quality=quality
                            )
                            display.success(f"JSON report generated: {json_path}")

                    except Exception as e:
                        display.error(f"Failed to generate report: {e}")
                        if verbose:
                            import traceback

                            traceback.print_exc()
            else:
                display.info(f"Would generate {suite.total_tests} tests (dry-run)")

            # Handle exit code
            if exit_code and not dry_run:
                # Check for verification failures
                failed_files = [tf for tf in suite.test_files if not tf.verified]
                if failed_files:
                    display.error(f"{len(failed_files)} files failed verification")
                    sys.exit(1)
        else:
            # Interactive mode
            run_interactive_generation(generator, components, auto_accept=auto)

    except KeyboardInterrupt:
        display.warning("\nGeneration interrupted")
        sys.exit(130)
    except Exception as e:
        display.error(f"Generation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


REPO_MARKERS = (".git", "pyproject.toml", "setup.py", "setup.cfg", ".code2test")


def find_repo_root(target: Path) -> Path:
    """
    Find the project root for a file or directory to test.

    Imports, the tests/ directory and the .code2test database are all relative
    to this root, so testing a subdirectory or a single file still produces
    `from pkg.mod import x` imports and writes to the project's tests/.
    """
    start = target if target.is_dir() else target.parent
    for directory in (start, *start.parents):
        if any((directory / marker).exists() for marker in REPO_MARKERS):
            return directory
    cwd = Path.cwd().resolve()
    if start == cwd or cwd in start.parents:
        return cwd
    return start


def _relative_dir_patterns(directory: str, repo_path: Path) -> List[str]:
    """The output directory as an exclude pattern relative to the project root."""
    path = Path(directory)
    if path.is_absolute():
        try:
            path = path.relative_to(repo_path)
        except ValueError:
            return []  # outside the project: never analyzed anyway
    text = path.as_posix().strip("/")
    return [] if text in ("", ".") else [text]


def _is_within(file_path: str, repo_path: Path, target: Path) -> bool:
    """True if a component's file is the target file or inside the target directory."""
    path = Path(file_path)
    if not path.is_absolute():
        path = repo_path / path
    path = path.resolve()
    return path == target or target in path.parents


def show_run_metrics(metrics) -> None:
    """Print what the run produced, against the MVP targets."""
    from rich.table import Table
    from code2test.core.metrics import target_rows

    summary = metrics.summary()
    table = Table(title="Generation Results")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    def pct(value) -> str:
        return "n/a" if value is None else f"{value:.0%}"

    table.add_row("Components", str(summary["components"]))
    table.add_row(
        "Components with passing tests",
        f"{summary['components_with_tests']} ({pct(summary['acceptance_rate'])})",
    )
    if summary["components_reused"]:
        table.add_row("  of which verified in an earlier run", str(summary["components_reused"]))
    if summary["skipped_low_confidence"]:
        table.add_row("Skipped (intent below --confidence)", str(summary["skipped_low_confidence"]))
    table.add_row("Tests generated", str(summary["tests_generated"]))
    table.add_row(
        "Passed on first run",
        f"{summary['first_run_passed']} ({pct(summary['first_run_pass_rate'])})",
    )
    table.add_row("Tests kept", str(summary["tests_kept"]))
    table.add_row("  of which xfail (possible bugs)", str(summary["tests_xfail"]))
    table.add_row("Tests dropped", str(summary["tests_dropped"]))
    table.add_row("Repair rounds", str(summary["repair_rounds"]))
    if summary["llm_failures"]:
        table.add_row("Components where generation failed", str(summary["llm_failures"]))
    console.print(table)

    for name, value, target, met in target_rows(
        {
            "acceptance_rate": summary["acceptance_rate"],
            "first_run_pass_rate": summary["first_run_pass_rate"],
        }
    ):
        if value is None:
            continue
        mark = "[green]✓[/green]" if met else "[yellow]✗[/yellow]"
        console.print(f"{mark} {name.replace('_', ' ')}: {value:.0%} (MVP target {target:.0%})")
