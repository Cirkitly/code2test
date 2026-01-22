"""
Test generation command for Code2Test CLI.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from code2test.cli.display import DisplayManager
from code2test.cli.interactive import InteractiveSession, run_interactive_generation
from code2test.cli.config_manager import ConfigManager
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
    "--exit-code/--no-exit-code",
    default=False,
    help="Return non-zero exit code if tests fail or verification fails"
)
@click.option(
    "--report",
    type=click.Choice(["none", "html", "json", "all"]),
    default="none",
    help="Generate reports after test generation"
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
    exit_code: bool,
    report: str,
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
    
    # Load configuration
    config_manager = ConfigManager()
    if not config_manager.load() or not config_manager.is_configured():
        display.warning("Code2Test is not fully configured.")
        display.info("Usage may fail if API keys are missing. Run 'code2test config set' to configure.")
    
    # Set API key in environment for agents
    api_key = config_manager.get_api_key()
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        # Support for Gemini/Google models which might look for these keys
        os.environ["GEMINI_API_KEY"] = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
    
    # Resolve paths
    repo_path = Path(path).resolve()
    
    # Get configured model
    cli_config = config_manager.get_config()
    main_model = cli_config.main_model if cli_config and cli_config.main_model else None
    
    # If no model configured, infer from env/keys
    # If no model configured, infer from env/keys
    if not main_model:
        llm_backend = os.environ.get("LLM_BACKEND", "").lower()
        azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        
        # Check for Azure configuration first (explicit override)
        if llm_backend == "azure" or (azure_deployment and os.environ.get("AZURE_OPENAI_ENDPOINT")):
            if azure_deployment:
                main_model = f"azure:{azure_deployment}"
                # Ensure API version is available for clients that need it
                if os.environ.get("AZURE_OPENAI_API_VERSION"):
                    os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]
                else:
                    # Default to a version that supports tool_choice='required'
                    # See: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#chat-completions
                    default_version = "2024-06-01"
                    if not os.environ.get("OPENAI_API_VERSION"):
                         os.environ["OPENAI_API_VERSION"] = default_version
                         display.info(f"Using default Azure API version: {default_version}")
                display.info(f"Detected Azure configuration, using deployment: {azure_deployment}")
            else:
                display.warning("Azure backend detected but AZURE_OPENAI_DEPLOYMENT is missing.")
                main_model = "openai:gpt-4o-mini"
        
        # Then check for Google API Key
        elif api_key and api_key.startswith("AIza"):
            # Google API key detected
            main_model = "google-gla:gemini-2.0-flash-exp"
            display.info("Detected Google API key, using Gemini 2.0 Flash")
            
        else:
            main_model = "openai:gpt-4o-mini"
    
    display.info(f"Using model: {main_model}")
    display.info(f"Analyzing: {repo_path}")
    
    try:
        # Create configuration
        config = GenerationConfig(
            confidence_threshold=confidence,
            auto_accept=auto,
            dry_run=dry_run,
            output_dir=output_dir,
            framework=TestFramework.PYTEST if framework == "pytest" else TestFramework.UNITTEST,
            model=main_model,
        )
        
        # Build include/exclude patterns
        include_patterns = [include] if include else None
        
        # More specific default exclude patterns to avoid excluding the repo itself if it has "test" in the name
        default_excludes = ["tests", "test", "*_test.py", "test_*.py", "*__pycache__*", "*.pyc", ".git", ".tox", ".env", "venv"]
        exclude_patterns = [exclude] if exclude else default_excludes
        
        # Analyze codebase
        display.info("Parsing codebase...")
        
        # Use the existing dependency analyzer
        # Use the existing dependency analyzer
        # We need to construct Config correctly as it requires many fields
        # and patterns go into agent_instructions
        agent_instructions = {
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns
        }
        
        repo_config = Config(
            repo_path=str(repo_path),
            output_dir=output_dir,
            dependency_graph_dir=f"{output_dir}/dependency_graphs",
            docs_dir=f"{output_dir}/docs",
            max_depth=2,
            llm_base_url="", # Not used for static analysis
            llm_api_key="",
            main_model="",
            cluster_model="",
            agent_instructions=agent_instructions
        )
        
        builder = DependencyGraphBuilder(repo_config)
        components, leaf_nodes = builder.build_dependency_graph()
        
        if not components:
            display.warning("No components found to analyze")
            sys.exit(0)
            
        display.success(f"Found {len(components)} components")
        
        # Convert Node objects to dictionaries for compatibility
        # and map 'depends_on' to 'dependencies'
        components_dict = {}
        for k, v in components.items():
            if hasattr(v, 'model_dump'):
                data = v.model_dump()
            else:
                data = v.dict()
            
            # Map depends_on to dependencies
            if 'depends_on' in data:
                data['dependencies'] = list(data['depends_on'])
            else:
                data['dependencies'] = []
                
            components_dict[k] = data
            
        components = components_dict
        
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
                
                # Handle reporting
                if report != "none":
                    display.info(f"Generating {report} report...")
                    try:
                        from code2test.reporting import HTMLReportGenerator, JSONReportGenerator
                        
                        report_dir = Path(output_dir) / "reports"
                        report_dir.mkdir(parents=True, exist_ok=True)
                        
                        if report in ["html", "all"]:
                            html_path = report_dir / "report.html"
                            html_gen = HTMLReportGenerator()
                            html_gen.generate_report(suite, generator.intent_db.get_all_intents_dict(), str(html_path))
                            display.success(f"HTML report generated: {html_path}")
                            
                        if report in ["json", "all"]:
                            json_path = report_dir / "report.json"
                            json_gen = JSONReportGenerator()
                            json_gen.generate_report(suite, generator.intent_db.get_all_intents_dict(), str(json_path))
                            display.success(f"JSON report generated: {json_path}")
                            
                    except Exception as e:
                        display.error(f"Failed to generate report: {e}")
                        if verbose:
                            import traceback
                            traceback.print_exc()
            else:
                display.info(f"Would generate {suite.total_tests} tests (dry-run)")
                
            # Handle exit code
            if exit_code and not dry_run:
                # Check for verification failures
                failed_files = [tf for tf in suite.test_files if not tf.verified]
                if failed_files:
                    display.error(f"{len(failed_files)} files failed verification")
                    sys.exit(1)
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
