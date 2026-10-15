"""
Init command for Code2Test.
"""

from pathlib import Path
from typing import Optional, Tuple

import click
from rich.prompt import Confirm

from code2test.cli.display import DisplayManager
from code2test.cli.utils.project_config import (
    PROJECT_DEFAULTS,
    project_config_path,
    write_project_settings,
)


@click.command("init")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True), default=".")
@click.option(
    "--confidence",
    type=click.FloatRange(0.0, 1.0),
    default=None,
    help=f"Intent confidence needed to generate tests in --auto mode (default {PROJECT_DEFAULTS['confidence_threshold']})",
)
@click.option(
    "--output-dir",
    type=str,
    default=None,
    help=f"Where generated tests are written (default {PROJECT_DEFAULTS['output_dir']})",
)
@click.option(
    "--exclude",
    type=str,
    multiple=True,
    help="Glob pattern of files to leave out of the analysis (repeatable)",
)
def init_command(
    path: str, confidence: Optional[float], output_dir: Optional[str], exclude: Tuple[str, ...]
) -> None:
    """
    Save project settings for 'code2test test' in .code2test/config.json.

    'code2test test' uses these settings as its defaults: the confidence
    threshold, the output directory and extra exclude patterns. Options
    given to 'code2test test' still take precedence. Edit the file to
    change them later.

    \b
    Examples:
        code2test init
        code2test init --confidence 0.7 --exclude "*migrations*"
    """
    display = DisplayManager()
    project_root = Path(path).resolve()
    config_file = project_config_path(project_root)

    if config_file.exists() and not Confirm.ask(f"{config_file} already exists. Overwrite?"):
        display.info("Aborted initialization.")
        return

    if not any(project_root.rglob("*.py")):
        display.warning("No Python files found; Code2Test generates tests for Python code only.")

    settings = {
        "confidence_threshold": PROJECT_DEFAULTS["confidence_threshold"]
        if confidence is None
        else confidence,
        "output_dir": output_dir or PROJECT_DEFAULTS["output_dir"],
        "exclude_patterns": list(exclude),
    }
    written = write_project_settings(project_root, settings)

    display.success(f"Saved project settings to {written}")
    display.info("Run 'code2test test .' to start generating tests.")
