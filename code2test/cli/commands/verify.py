"""
Verify command for Code2Test CLI.
"""

from pathlib import Path
import click
from rich.console import Console

from code2test.cli.display import DisplayManager

console = Console()


@click.command("verify")
@click.argument("path", type=click.Path(exists=True), default="tests")
@click.option("--diagnose", is_flag=True, help="Diagnose and explain failures")
@click.option("--fix", is_flag=True, help="Attempt to auto-fix failed tests")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def verify_command(
    path: str,
    diagnose: bool,
    fix: bool,
    verbose: bool
) -> None:
    """
    Run and verify generated tests.
    
    Executes tests and provides diagnosis for any failures.
    
    \b
    Examples:
        code2test verify tests/           # Verify all tests
        code2test verify --diagnose       # Diagnose failures
    """
    display = DisplayManager(quiet=not verbose)
    
    test_path = Path(path).resolve()
    display.info(f"Verifying tests in: {test_path}")
    
    # Import verifier
    from code2test.adapters.python.pytest_adapter import PytestAdapter
    
    # Determine adapter based on file type or config (defaulting to pytest for now)
    # TODO: Detect framework or take as arg
    adapter = PytestAdapter(str(test_path.parent))
    results = adapter.run_tests(str(test_path))
    
    # Display results
    summary = results.get("summary", {})
    
    if results.get("success"):
        display.success(f"All {summary.get('total', 0)} tests passed!")
    else:
        display.warning(
            f"{summary.get('passed', 0)}/{summary.get('total', 0)} tests passed"
        )
        
        if results.get("stdout"):
            console.print("\n[dim]Output:[/dim]")
            console.print(results["stdout"][-1000:])
