"""
Code2Test CLI Display Module

Rich terminal rendering for test generation output.
"""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.live import Live

from code2test.core.models import (
    Intent,
    TestCase,
    TestFile,
    TestStatus,
    Diagnosis,
    DiagnosisCause,
    VerificationResult,
)


# Global console instance
console = Console()


class DisplayManager:
    """Manages rich terminal output for Code2Test."""
    
    def __init__(self, quiet: bool = False):
        """
        Initialize display manager.
        
        Args:
            quiet: Suppress non-essential output
        """
        self.console = Console()
        self.quiet = quiet
    
    def show_intent(self, intent: Intent, component_name: str = "") -> None:
        """
        Display inferred intent with confidence indicator.
        
        Args:
            intent: Intent to display
            component_name: Name of the component
        """
        # Color code confidence
        if intent.confidence >= 0.8:
            color = "green"
            indicator = "●"
        elif intent.confidence >= 0.6:
            color = "yellow"
            indicator = "◐"
        else:
            color = "red"
            indicator = "○"
        
        name = component_name or intent.component_id
        
        self.console.print()
        self.console.print(f"▶ [bold]{name}[/bold]")
        self.console.print(
            f"  Intent [{color}]({intent.confidence:.0%} confidence)[/{color}]:"
        )
        self.console.print(f'  [italic]"{intent.intent_text}"[/italic]')
        
        # Show evidence summary
        if intent.evidence.docstring:
            self.console.print(f"  [dim]├─ Docstring: ✓[/dim]")
        if intent.evidence.type_hints:
            self.console.print(f"  [dim]├─ Type hints: ✓[/dim]")
        if intent.evidence.naming_signals:
            self.console.print(f"  [dim]└─ Naming: {', '.join(intent.evidence.naming_signals)}[/dim]")
    
    def show_test_preview(self, test_file: TestFile) -> None:
        """
        Display test file preview.
        
        Args:
            test_file: Generated test file
        """
        self.console.print()
        self.console.print(f"  Generated [bold]{len(test_file.test_cases)}[/bold] tests:")
        
        for tc in test_file.test_cases:
            icon = self._get_status_icon(tc.status)
            self.console.print(f"  {icon} {tc.name}")
    
    def show_test_code(self, test_case: TestCase) -> None:
        """
        Display test case code with syntax highlighting.
        
        Args:
            test_case: Test case to display
        """
        syntax = Syntax(
            test_case.test_code,
            "python",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        self.console.print()
        self.console.print(Panel(syntax, title=test_case.name, border_style="dim"))
    
    def show_verification_result(self, result: VerificationResult) -> None:
        """
        Display verification results.
        
        Args:
            result: Verification result
        """
        self.console.print()
        self.console.print("Running tests...")
        
        for name in result.passed:
            self.console.print(f"✓ {name} [green]PASSED[/green]")
        
        for name in result.failed:
            self.console.print(f"✗ {name} [red]FAILED[/red]")
        
        for name in result.skipped:
            self.console.print(f"○ {name} [yellow]SKIPPED[/yellow]")
        
        # Summary
        total = result.total_tests
        passed = len(result.passed)
        self.console.print()
        
        if result.all_passed:
            self.console.print(
                f"[green]All {total} tests passed.[/green]"
            )
        else:
            self.console.print(
                f"[yellow]{passed}/{total} tests passed.[/yellow]"
            )
    
    def show_diagnosis_panel(self, diagnosis: Diagnosis) -> None:
        """
        Display diagnosis in a panel.
        
        Args:
            diagnosis: Diagnosis to display
        """
        cause_colors = {
            DiagnosisCause.TEST_WRONG: "yellow",
            DiagnosisCause.CODE_BUG: "red",
            DiagnosisCause.INTENT_WRONG: "magenta",
        }
        
        cause_labels = {
            DiagnosisCause.TEST_WRONG: "Test incorrectly implements intent",
            DiagnosisCause.CODE_BUG: "Potential bug in source code",
            DiagnosisCause.INTENT_WRONG: "Intent doesn't match actual behavior",
        }
        
        color = cause_colors.get(diagnosis.cause, "white")
        label = cause_labels.get(diagnosis.cause, str(diagnosis.cause))
        
        content = Text()
        content.append(f"{diagnosis.explanation}\n\n")
        content.append(f"Likely cause: ", style="bold")
        content.append(f"{diagnosis.cause.value} ", style=f"bold {color}")
        content.append(f"({diagnosis.confidence:.0%})")
        
        if diagnosis.suggested_fix:
            content.append(f"\n\nSuggested fix: ", style="bold")
            content.append(diagnosis.suggested_fix)
        
        panel = Panel(
            content,
            title="Diagnosis",
            border_style=color,
        )
        self.console.print(panel)
    
    def show_prompt(self, prompt_text: str, choices: str) -> None:
        """
        Display action prompt.
        
        Args:
            prompt_text: Prompt message
            choices: Available choices (e.g., "[y] Accept  [n] Skip")
        """
        self.console.print()
        self.console.print(f"[dim]{choices}[/dim]")
    
    def show_summary_table(self, stats: Dict[str, Any]) -> None:
        """
        Display summary statistics table.
        
        Args:
            stats: Statistics dictionary
        """
        table = Table(title="Generation Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Components", str(stats.get("total_intents", 0)))
        table.add_row("Tests Generated", str(stats.get("total_test_cases", 0)))
        table.add_row("Test Files", str(stats.get("total_test_files", 0)))
        table.add_row("Verified", str(stats.get("verified_files", 0)))
        table.add_row("Avg Confidence", f"{stats.get('avg_confidence', 0):.0%}")
        
        self.console.print()
        self.console.print(table)
    
    def show_test_tree(self, test_files: List[TestFile]) -> None:
        """
        Display hierarchical test structure.
        
        Args:
            test_files: List of test files
        """
        tree = Tree("[bold]Generated Tests[/bold]")
        
        for tf in test_files:
            file_node = tree.add(f"[cyan]{tf.path}[/cyan]")
            for tc in tf.test_cases:
                icon = self._get_status_icon(tc.status)
                file_node.add(f"{icon} {tc.name}")
        
        self.console.print()
        self.console.print(tree)
    
    def show_progress(self, description: str) -> Progress:
        """
        Create a progress bar.
        
        Args:
            description: Progress description
            
        Returns:
            Progress context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        )
    
    def info(self, message: str) -> None:
        """Display info message."""
        if not self.quiet:
            self.console.print(f"[blue]ℹ[/blue] {message}")
    
    def success(self, message: str) -> None:
        """Display success message."""
        self.console.print(f"[green]✓[/green] {message}")
    
    def warning(self, message: str) -> None:
        """Display warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def error(self, message: str) -> None:
        """Display error message."""
        self.console.print(f"[red]✗[/red] {message}")
    
    def _get_status_icon(self, status: TestStatus) -> str:
        """Get icon for test status."""
        icons = {
            TestStatus.PENDING: "○",
            TestStatus.PASSED: "[green]✓[/green]",
            TestStatus.FAILED: "[red]✗[/red]",
            TestStatus.SKIPPED: "[yellow]○[/yellow]",
            TestStatus.XFAIL: "[magenta]○[/magenta]",
        }
        return icons.get(status, "?")
