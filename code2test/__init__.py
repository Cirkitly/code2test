"""
Code2Test: Intelligent Test Generation for Legacy Codebases.

This package provides a CLI tool for generating comprehensive test suites
for codebases lacking tests using intent-first AI analysis.

Built on FSoft AI4Code's CodeWiki framework.
"""

__version__ = "0.1.0"
__author__ = "Code2Test Contributors"
__license__ = "MIT"

from code2test.cli.main import cli

__all__ = ["cli", "__version__"]
