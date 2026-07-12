"""Code2Test: Intelligent Test Generation for Legacy Codebases.

This package provides a CLI tool for generating comprehensive test suites
for codebases lacking tests using intent-first AI analysis.

Built on FSoft AI4Code's CodeWiki framework.
"""

__version__ = "1.0.0"
__author__ = "Code2Test Contributors"
__license__ = "MIT"

__all__ = ["__version__"]


def get_cli():
    """Lazy accessor for the CLI; avoids importing click + every subcommand at
    package import time. Use this to obtain the click Group from outside
    package-init context (tests, IDE, etc.)."""
    from code2test.cli.main import cli
    return cli

