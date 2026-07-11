"""Smoke tests verifying that every documented CLI subcommand resolves and
returns help text without raising.

These tests are the M0 verification gate for plan §M0.4. They use
click.testing.CliRunner to invoke the CLI in-process rather than shelling out.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from code2test.cli.main import cli

SUBCOMMAND_HELP = [
    "test --help",
    "verify --help",
    "intent --help",
    "report --help",
    "init --help",
    "config --help",
    "generate --help",
    "--help",
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("cmd", SUBCOMMAND_HELP)
def test_help_for_each_subcommand(runner, cmd):
    args = cmd.split()
    result = runner.invoke(cli, args, catch_exceptions=False)
    assert result.exit_code == 0, f"{cmd!r} failed:\n{result.output}\n{result.exception if result.exception else ''}"
    assert result.output.strip(), f"{cmd!r} returned empty stdout"


def test_root_help_lists_all_subcommands(runner):
    """`code2test --help` must show every v1.0 subcommand."""
    result = runner.invoke(cli, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0
    for name in ["test", "verify", "intent", "report", "init"]:
        assert name in result.output, f"missing subcommand {name!r} in --help"


def test_lazy_loading_does_not_load_siblings_on_invoke(runner):
    """Invoking `verify --help` must not load the `generate` command module.

    This is the architectural intent of M0.4: per-command imports are
    resolved on demand, not at CLI startup. Click's --help rendering does
    enumerate all commands, so we test on the invocation boundary instead.
    """
    import sys
    for k in list(sys.modules):
        if k.startswith("code2test.cli.commands"):
            del sys.modules[k]

    result = runner.invoke(cli, ["verify", "--help"], catch_exceptions=False)
    assert result.exit_code == 0

    loaded = [m for m in sys.modules if m.startswith("code2test.cli.commands.")]
    assert "code2test.cli.commands.generate" not in loaded, (
        f"generate module was loaded during 'verify --help': {loaded}"
    )
    assert "code2test.cli.commands.verify" in loaded, (
        "verify module should be loaded after invocation"
    )


def test_package_init_does_not_import_cli(runner):
    """`import code2test` must NOT pull cli/main into sys.modules.

    This catches accidental reintroduction of the eager import on
    code2test/__init__.py.8.
    """
    import sys
    for k in list(sys.modules):
        if k.startswith("code2test.cli"):
            del sys.modules[k]

    import code2test as c2t
    assert "code2test.cli.main" not in sys.modules, (
        "code2test package import must be lazy; got cli.main in sys.modules"
    )
    assert c2t.__version__ == "0.1.0"
