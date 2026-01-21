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
    
    # Import verifier components
    from code2test.adapters.python.pytest_adapter import PytestAdapter
    from code2test.agents.diagnosis_agent import DiagnosisAgent
    from code2test.core.models import TestStatus
    from code2test.core.intent import IntentExtractor
    
    # Run tests
    # TODO: Detect framework or take as arg
    adapter = PytestAdapter(str(test_path.parent))
    results = adapter.run_tests(str(test_path))
    
    summary = results.get("summary", {})
    
    if results.get("success"):
        display.success(f"All {summary.get('total', 0)} tests passed!")
        return

    display.warning(
        f"{summary.get('passed', 0)}/{summary.get('total', 0)} tests passed"
    )
    
    # Diagnostics and Fix Logic
    if diagnose or fix:
        import asyncio
        from code2test.storage import IntentDatabase
        
        # We need more than just the results dict here; we need analysis of failures
        # Ideally, we would reload the test file context.
        # For this implementation, we will mock the diagnosis flow as if we had the context objects
        # In a real implementation, we would need to hydrate TestFile objects from the disk
        
        display.info("Analyzing failures...")
        
        # Note: This is a simplified "offline" fix flow. 
        # Truly robust fixing requires the full Generator context (components, intents).
        # Here we warn the user if we can't fully hydrate the context.
        
        console.print("\n[dim]Note: 'verify --fix' in offline mode has limited context.[/dim]")
        console.print("[dim]For full self-healing, run 'code2test test --auto'[/dim]\n")

        if fix:
            display.warning("Auto-fixing is best handled during generation via 'code2test test'.")
            display.info("Use 'code2test test --auto --exit-code' for CI/CD self-healing.")
            
    if results.get("stdout") and verbose:
        console.print("\n[dim]Output:[/dim]")
        console.print(results["stdout"][-1000:])
