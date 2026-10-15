"""
Per-project settings in .code2test/config.json, written by `code2test init`.

`code2test test` uses them as defaults; options given on the command line win.
"""

import json
from pathlib import Path
from typing import Any, Dict

import click

PROJECT_DEFAULTS: Dict[str, Any] = {
    "confidence_threshold": 0.6,
    "output_dir": "tests",
    "exclude_patterns": [],
}


def project_config_path(repo_root: Path) -> Path:
    return Path(repo_root) / ".code2test" / "config.json"


def load_project_settings(repo_root: Path) -> Dict[str, Any]:
    """
    The settings saved for this project, or an empty dict when there are none.

    Keys other than those in PROJECT_DEFAULTS are ignored, so files written by older
    versions (which also stored a language and framework) still load.

    Raises:
        click.ClickException: If the file cannot be read or a setting has the wrong type
    """
    path = project_config_path(repo_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Cannot read {path}: {e}")
    if not isinstance(data, dict):
        raise click.ClickException(f"{path} must contain a JSON object")

    settings: Dict[str, Any] = {}
    if "confidence_threshold" in data:
        value = data["confidence_threshold"]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.0 <= value <= 1.0
        ):
            raise click.ClickException(f"{path}: confidence_threshold must be a number from 0 to 1")
        settings["confidence_threshold"] = float(value)
    if "output_dir" in data:
        if not isinstance(data["output_dir"], str) or not data["output_dir"]:
            raise click.ClickException(f"{path}: output_dir must be a non-empty string")
        settings["output_dir"] = data["output_dir"]
    if "exclude_patterns" in data:
        value = data["exclude_patterns"]
        if not isinstance(value, list) or not all(isinstance(p, str) for p in value):
            raise click.ClickException(f"{path}: exclude_patterns must be a list of strings")
        settings["exclude_patterns"] = value
    return settings


def write_project_settings(repo_root: Path, settings: Dict[str, Any]) -> Path:
    """Write settings to .code2test/config.json and return its path."""
    path = project_config_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return path
