"""
Report command for Code2Test CLI.
"""

from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from code2test.cli.display import DisplayManager

console = Console()


@click.command("report")
@click.argument("type", type=click.Choice(["summary", "coverage"]), default="summary")
@click.option("--format", type=click.Choice(["text", "html", "json"]), default="text")
@click.option("--output", type=click.Path(), default="report.html")
def report_command(
    type: str,
    format: str,
    output: str
) -> None:
    """
    Generate quality and coverage reports.
    
    \b
    Examples:
        code2test report summary          # View summary report
        code2test report coverage --format html   # Generate HTML coverage report
    """
    display = DisplayManager()
    
    # Import storage
    from code2test.storage import IntentDatabase, TestRegistry
    
    # Find database
    db_path = Path.cwd() / ".code2test" / "code2test.db"
    
    if not db_path.exists():
        display.error("No database found. Run 'code2test test' first.")
        return
        
    db = IntentDatabase(str(db_path))
    registry = TestRegistry(str(db_path))
    
    intents = db.get_all_intents()
    # Mock retrieval of tests from registry (registry API needs to support listing all)
    # For now we'll do a basic stats report
    
    total_intents = len(intents)
    high_confidence = len([i for i in intents if i.confidence >= 0.8])
    medium_confidence = len([i for i in intents if 0.5 <= i.confidence < 0.8])
    low_confidence = len([i for i in intents if i.confidence < 0.5])
    
    if type == "summary":
        table = Table(title="Code2Test Summary Report")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Intents Extracted", str(total_intents))
        table.add_row("High Confidence (>80%)", str(high_confidence))
        table.add_row("Medium Confidence (>50%)", str(medium_confidence))
        table.add_row("Low Confidence (<50%)", str(low_confidence))
        
        # Add test stats if we had them easily accessible
        # tests = registry.get_all_tests() ...
        
        console.print(table)
        
    elif type == "coverage":
        display.info("Coverage reporting not yet implemented.")
