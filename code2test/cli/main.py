"""
Main CLI application for Code2Test using Click framework.

Subcommands are loaded lazily: only when a user actually invokes them is the
corresponding command module imported. This keeps `code2test --help` cheap and
isolates per-command import failures from package startup.
"""

import importlib
from typing import Callable

import click


class LazyGroup(click.Group):
    """A click Group whose subcommands are imported on first resolution.

    Two patterns are required by Click:

    * ``list_commands(ctx)`` enumerates names — must use ``self.lazy_subcommands``
      plus whatever is already registered. Called for help rendering.
    * ``get_command(ctx, name)`` resolves a name to a Command object, importing
      the module on first call. This is what actually defers the work.
    """

    def __init__(self, *args, lazy_subcommands: dict | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_subcommands: dict = lazy_subcommands or {}

    def list_commands(self, ctx):
        names = set(super().list_commands(ctx))
        names.update(self.lazy_subcommands)
        return sorted(names)

    def get_command(self, ctx, cmd_name):
        if cmd_name in self.lazy_subcommands:
            module_path, attr = self.lazy_subcommands[cmd_name]
            module = importlib.import_module(module_path)
            cmd: click.Command = getattr(module, attr)
            return cmd
        return super().get_command(ctx, cmd_name)


@click.group(cls=LazyGroup)
@click.version_option(version="0.1.0", prog_name="Code2Test")
@click.pass_context
def cli(ctx):
    """Code2Test: Intelligent Test Generation for Legacy Codebases.

    Generate comprehensive test suites using intent-first AI analysis.
    Supports Python, Java, JavaScript, TypeScript, C, C++, and C#.

    \b
    Quick Start:
      code2test test src/             # Generate tests interactively
      code2test test --auto .         # Auto-accept high-confidence tests
      code2test verify tests/         # Verify generated tests
      code2test intent show auth      # View inferred intents
    """
    ctx.ensure_object(dict)


@cli.command()
def version():
    """Display version information."""
    click.echo("Code2Test v0.1.0")
    click.echo("Intent-first test generation for legacy codebases")
    click.echo("Built on FSoft AI4Code's CodeWiki framework")


# Subcommand registry. Modules are imported only when the named subcommand is
# resolved, never at package load. Optional subcommands (config-group) live
# under nested registration once their module is loaded.
_LAZY_SUBCOMMANDS: dict[str, tuple[str, str]] = {
    "config": ("code2test.cli.commands.config", "config_group"),
    "generate": ("code2test.cli.commands.generate", "generate_command"),
    "test": ("code2test.cli.commands.test", "test_command"),
    "verify": ("code2test.cli.commands.verify", "verify_command"),
    "intent": ("code2test.cli.commands.intent", "intent_command"),
    "report": ("code2test.cli.commands.report", "report_command"),
    "init": ("code2test.cli.commands.init", "init_command"),
}

# Inject the lazy subcommand table on the group without triggering imports.
cli.lazy_subcommands = _LAZY_SUBCOMMANDS


def main():
    """Entry point for the CLI."""
    import sys
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
