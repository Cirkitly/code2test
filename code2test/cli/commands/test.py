"""
Test generation command for Code2Test CLI.
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from code2test.cli.display import DisplayManager
from code2test.cli.interactive import InteractiveSession, run_interactive_generation
from code2test.core import TestGenerator, GenerationConfig, TestFramework
from code2test.src.be.dependency_analyzer import DependencyGraphBuilder
from code2test.src.config import Config

logger = logging.getLogger(__name__)
console = Console()


@click.command("test")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option(
    "--auto",
    is_flag=True,
    default=False,
    help="Auto-accept high-confidence tests without prompting"
)
@click.option(
    "--confidence",
    type=float,
    default=0.6,
    help="Minimum confidence threshold for auto-acceptance (0.0-1.0)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be generated without writing files"
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="tests",
    help="Output directory for generated tests"
)
@click.option(
    "--framework",
    type=click.Choice(["pytest", "unittest"]),
    default="pytest",
    help="Test framework to use"
)
@click.option(
    "--include",
    type=str,
    default=None,
    help="Glob pattern for files to include (e.g., '*.py')"
)
@click.option(
    "--exclude",
    type=str,
    default=None,
    help="Glob pattern for files to exclude (e.g., '*test*')"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging"
)
def test_command(
    path: str,
    auto: bool,
    confidence: float,
    dry_run: bool,
    output_dir: str,
    framework: str,
    include: Optional[str],
    exclude: Optional[str],
    verbose: bool
) -> None:
    """
    Generate tests for a code repository or module.
    
    Analyzes the code using intent-first analysis and generates comprehensive
    test suites with human-in-the-loop verification.
    
    \b
    Examples:
        code2test test src/auth/          # Generate tests for auth module
        code2test test --auto .           # Auto-generate for entire repo
        code2test test --dry-run src/     # Preview without writing
        code2test test --confidence 0.8   # Only accept high-confidence
    """
    display = DisplayManager(quiet=not verbose)
    
    # Setup logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    
    # Validate confidence
    if not 0.0 <= confidence <= 1.0:
        display.error("Confidence must be between 0.0 and 1.0")
        sys.exit(1)
    
    # Resolve paths
    repo_path = Path(path).resolve()
    
    display.info(f"Analyzing: {repo_path}")
    
    try:
        # Create configuration
        config = GenerationConfig(
            confidence_threshold=confidence,
            auto_accept=auto,
            dry_run=dry_run,
            output_dir=output_dir,
            framework=TestFramework.PYTEST if framework == "pytest" else TestFramework.UNITTEST,
        )
        
        # Build include/exclude patterns
        include_patterns = [include] if include else None
        exclude_patterns = [exclude] if exclude else ["*test*", "*__pycache__*", "*.pyc"]
        
        # Analyze codebase
        display.info("Parsing codebase...")
        
        # Use the existing dependency analyzer
        repo_config = Config(
            repo_path=str(repo_path),
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        
        builder = DependencyGraphBuilder(repo_config)
        components_data = builder.build()
        
        if not components_data or not components_data.get("components"):
            display.warning("No components found to analyze")
            sys.exit(0)
        
        components = components_data.get("components", {})
        display.success(f"Found {len(components)} components")
        
        # Create generator
        generator = TestGenerator(
            repo_path=str(repo_path),
            config=config,
        )
        
        if auto:
            # Non-interactive batch mode
            display.info("Running in auto mode...")
            
            async def run_batch():
                suite = await generator.generate_tests_for_module(
                    str(repo_path),
                    components
                )
                return suite
            
            suite = asyncio.run(run_batch())
            
            display.show_summary_table(generator.get_stats())
            
            if not dry_run:
                display.success(f"Generated {suite.total_tests} tests in {len(suite.test_files)} files")
            else:
                display.info(f"Would generate {suite.total_tests} tests (dry-run)")
        else:
            # Interactive mode
            run_interactive_generation(generator, components, auto_accept=auto)
        
    except KeyboardInterrupt:
        display.warning("\nGeneration interrupted")
        sys.exit(130)
    except Exception as e:
        display.error(f"Generation failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
