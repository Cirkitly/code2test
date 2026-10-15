"""
Code2Test: intent-first test generation for legacy Python code.

This package provides a CLI tool for generating comprehensive test suites
for Python code that lacks tests, using intent-first LLM analysis.

Dependency analysis derived from FSoft AI4Code's CodeWiki.
"""

__version__ = "0.1.0"
__author__ = "Code2Test Contributors"
__license__ = "MIT"

from code2test.cli.main import cli

__all__ = ["cli", "__version__"]
