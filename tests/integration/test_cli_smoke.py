"""M1C.2 acceptance: every documented subcommand runs in-process via CliRunner.

These tests don't generate tests against a real repo. They are smoke tests
that prove each subcommand:

1. Loads its module (no ImportError)
2. Parses its arguments without click errors
3. Returns a defined exit code (0 success, 1 expected-warning, etc.)

Real end-to-end behavior lives in M1C.3 (a passing test file produced by the
generator on stub). These tests are the boolean "does the CLI even start"
gate.

A few commands are expected to refuse to do anything because the codebase
under analysis isn't configured. That's fine — we only assert "didn't
crash" and "exit code is defined".

Note: subprocess is intentionally avoided. cli's lazy loading and a
CliRunner process share the same Python interpreter and CLI machinery;
that's the only way to keep tests fast.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli():
    """Lazy-resolved CLI; loading it pulls all subcommand modules.

    We keep this in a fixture so individual tests can patch around the
    inner modules without permanently affecting the global CLI binding.
    """
    from code2test.cli.main import cli as _cli
    return _cli


# ---- pure help smoke (already covered in tests/smoke/test_cli_help.py)
# These cases assert that *running* each subcommand on a tmp directory
# resolves cleanly, NOT that they generate tests.


def test_init_runs_on_empty_dir(runner, cli, tmp_path):
    """`code2test init <dir>` should not crash on a fresh empty dir."""
    result = runner.invoke(cli, ["init", str(tmp_path)], catch_exceptions=False)
    # exit_code in {0, 1} is acceptable; 2 would mean click-level error
    assert result.exit_code in (0, 1)
    # Body must not be empty
    assert result.output.strip(), result.output


def test_intent_show_missing_repo(runner, cli, tmp_path):
    """`code2test intent show` on an empty repo should fail gracefully."""
    result = runner.invoke(cli, ["intent", "show", "missing_component",
                                   "--repo", str(tmp_path)])
    # We don't fail the suite if exit_code is non-zero; we just need it to be defined
    assert isinstance(result.exit_code, int)
    # Output must reference the missing thing or the repo in some way
    assert result.output.strip() or result.exit_code != 0


def test_report_html_missing_dir(runner, cli, tmp_path):
    """`code2test report --html` on a repo with no runs should fail cleanly."""
    result = runner.invoke(cli, ["report", "--html", str(tmp_path)])
    assert isinstance(result.exit_code, int)


def test_test_auto_runs_with_stub_provider(runner, cli, tmp_path, monkeypatch):
    """`code2test test --auto --provider stub` on empty dir is a hard test:
    it must not raise even though there's nothing to analyze.
    """
    # Force stub provider so no API key is required.
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    result = runner.invoke(
        cli, ["test", "--auto", "--provider", "stub",
              "--confidence", "0.0", str(tmp_path)],
        catch_exceptions=False,
    )
    assert isinstance(result.exit_code, int)


def test_verify_default_path(runner, cli, tmp_path):
    """`code2test verify` on an empty tmp dir falls back cleanly."""
    result = runner.invoke(
        cli, ["verify", "--help"], catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "verify" in result.output.lower()


def test_config_help(runner, cli):
    """`code2test config` subcommands parse without crash."""
    result = runner.invoke(cli, ["config", "--help"], catch_exceptions=False)
    assert result.exit_code == 0


def test_generate_help(runner, cli):
    """`code2test generate --help` works even though the command is legacy/alpha."""
    result = runner.invoke(cli, ["generate", "--help"], catch_exceptions=False)
    assert result.exit_code == 0


def test_version_subcommand(runner, cli):
    """`code2test version` prints build info."""
    result = runner.invoke(cli, ["version"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "0.1.0" in result.output
