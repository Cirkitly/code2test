"""
Configuration commands for the Code2Test CLI.
"""

import json
import os
import sys
from typing import Optional

import click

from code2test.cli.config_manager import ConfigManager
from code2test.cli.utils.errors import ConfigurationError, handle_error, EXIT_CONFIG_ERROR
from code2test.cli.utils.validation import validate_api_key, validate_model_name, mask_api_key


@click.group(name="config")
def config_group():
    """Manage Code2Test configuration (API key and model)."""
    pass


@config_group.command(name="set")
@click.option(
    "--api-key",
    type=str,
    help="LLM API key (stored in the system keychain; exported as OPENAI_API_KEY when Code2Test runs)"
)
@click.option(
    "--main-model",
    type=str,
    help="Model for test generation, as a pydantic-ai model string (e.g. anthropic:claude-sonnet-5-5)"
)
def config_set(api_key: Optional[str], main_model: Optional[str]):
    """
    Set the API key and the model Code2Test uses.

    The API key is stored in your system keychain (macOS Keychain, Windows
    Credential Manager, or Linux Secret Service). The CODE2TEST_MODEL
    environment variable, when set, takes precedence over the saved model.

    Examples:

    \b
    # Key and model for test generation
    $ code2test config set --api-key sk-abc123 --main-model openai:gpt-4o-mini

    \b
    # Update only the API key
    $ code2test config set --api-key sk-new-key
    """
    try:
        if not api_key and not main_model:
            click.echo("No options provided. Use --help for usage information.")
            sys.exit(EXIT_CONFIG_ERROR)

        api_key = validate_api_key(api_key) if api_key else None
        main_model = validate_model_name(main_model) if main_model else None

        manager = ConfigManager()
        manager.load()  # Keep settings saved earlier
        manager.save(api_key=api_key, main_model=main_model)

        click.echo()
        if api_key:
            click.secho("✓ API key saved to system keychain", fg="green")
        if main_model:
            click.secho(f"✓ Main model: {main_model}", fg="green")
        click.echo("\n" + click.style("Configuration updated successfully.", fg="green", bold=True))

    except ConfigurationError as e:
        click.secho(f"\n✗ Configuration error: {e.message}", fg="red", err=True)
        sys.exit(e.exit_code)
    except Exception as e:
        sys.exit(handle_error(e))


@config_group.command(name="show")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def config_show(output_json: bool):
    """
    Display the current configuration.

    The API key is masked, showing only its first and last 4 characters.

    Examples:

    \b
    $ code2test config show
    $ code2test config show --json
    """
    try:
        manager = ConfigManager()
        if not manager.load():
            click.secho("\n✗ Configuration not found.", fg="red", err=True)
            click.echo("\nPlease run 'code2test config set' to configure your API key and model:")
            click.echo("  code2test config set --api-key <key> --main-model <model>")
            click.echo("\nFor more help: code2test config set --help")
            sys.exit(EXIT_CONFIG_ERROR)

        config = manager.get_config()
        api_key = manager.get_api_key()
        env_model = os.environ.get("CODE2TEST_MODEL")

        if output_json:
            output = {
                "api_key": mask_api_key(api_key) if api_key else "Not set",
                "main_model": config.main_model if config else "",
                "code2test_model_env": env_model or "",
                "config_file": str(manager.config_file_path),
            }
            click.echo(json.dumps(output, indent=2))
            return

        click.echo()
        click.secho("Code2Test Configuration", fg="blue", bold=True)
        click.echo("━" * 40)
        click.echo()
        if api_key:
            click.echo(f"  API Key:          {mask_api_key(api_key)} (in system keychain)")
        else:
            click.secho("  API Key:          Not set", fg="yellow")
        click.echo(f"  Main Model:       {(config.main_model if config else '') or 'Not set'}")
        if env_model:
            click.echo(f"  CODE2TEST_MODEL:  {env_model} (overrides the main model)")
        click.echo()
        click.echo(f"Configuration file: {manager.config_file_path}")
        click.echo()

    except Exception as e:
        sys.exit(handle_error(e))


@config_group.command(name="validate")
@click.option("--quick", is_flag=True, help="Skip the test request to the model")
@click.option("--verbose", "-v", is_flag=True, help="Show the full error on failure")
def config_validate(quick: bool, verbose: bool):
    """
    Check which model Code2Test will use and that it answers.

    Resolves the model exactly as 'code2test test' does, then sends it one
    short request (unless --quick).

    Examples:

    \b
    $ code2test config validate
    $ code2test config validate --quick
    """
    from code2test.cli.display import DisplayManager
    from code2test.cli.utils.model import resolve_model

    try:
        click.echo()
        model = resolve_model(DisplayManager())
        click.secho(f"✓ Model: {model}", fg="green")

        if quick:
            click.echo()
            return

        from pydantic_ai import Agent

        try:
            Agent(model).run_sync("Reply with the single word OK.")
        except Exception as e:
            message = str(e) if verbose else (str(e).splitlines() or [type(e).__name__])[0]
            click.secho(f"✗ The model did not answer: {message}", fg="red")
            sys.exit(EXIT_CONFIG_ERROR)

        click.secho("✓ The model answered a test request", fg="green")
        click.echo()

    except ConfigurationError as e:
        click.secho(f"\n✗ Configuration error: {e.message}", fg="red", err=True)
        sys.exit(e.exit_code)
    except Exception as e:
        sys.exit(handle_error(e, verbose=verbose))
