"""
Main CLI application for Code2Test using Click framework.
"""

import sys
import click
from pathlib import Path

from code2test import __version__


@click.group()
@click.version_option(version=__version__, prog_name="Code2Test")
@click.pass_context
def cli(ctx):
    """
    Code2Test: Intelligent Test Generation for Legacy Codebases.
    
    Generate comprehensive test suites using intent-first AI analysis.
    Supports Python, Java, JavaScript, TypeScript, C, C++, and C#.
    
    \b
    Quick Start:
      code2test test src/             # Generate tests interactively
      code2test test --auto .         # Auto-accept high-confidence tests
      code2test verify tests/         # Verify generated tests
      code2test intent show auth      # View inferred intents
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


@cli.command()
def version():
    """Display version information."""
    click.echo(f"Code2Test v{__version__}")
    click.echo("Intent-first test generation for legacy codebases")
    click.echo("Built on FSoft AI4Code's CodeWiki framework")
    

# Import commands
from code2test.cli.commands.config import config_group
from code2test.cli.commands.generate import generate_command
from code2test.cli.commands.test import test_command, verify_command, intent_command

# Register command groups
cli.add_command(config_group)
cli.add_command(generate_command, name="generate")  # Legacy docs command

# Register new test generation commands
cli.add_command(test_command)      # code2test test
cli.add_command(verify_command)    # code2test verify
cli.add_command(intent_command)    # code2test intent


def main():
    """Entry point for the CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.secho(f"\n✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
