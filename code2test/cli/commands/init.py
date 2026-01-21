"""
Init command for Code2Test.
"""

import json
from pathlib import Path
import click
from rich.prompt import Confirm, Prompt

from code2test.cli.display import DisplayManager

@click.command("init")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True), default=".")
def init_command(path: str) -> None:
    """
    Initialize Code2Test in a repository.
    
    Creates a .code2test configuration directory and detects project settings.
    """
    display = DisplayManager()
    project_root = Path(path).resolve()
    
    display.info(f"Initializing Code2Test in: {project_root}")
    
    config_dir = project_root / ".code2test"
    config_file = config_dir / "config.json"
    
    if config_file.exists():
        if not Confirm.ask("Configuration already exists. Overwrite?"):
            display.info("Aborted initialization.")
            return

    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Auto-detect language
    language = "python" # Default
    framework = "pytest"
    
    if (project_root / "package.json").exists():
        language = "javascript"
        framework = "jest"
        display.info("Detected JavaScript/TypeScript project")
    elif (project_root / "pom.xml").exists() or (project_root / "build.gradle").exists():
        language = "java"
        framework = "junit"
        display.info("Detected Java project")
    else:
        display.info("Detected Python project (default)")
        
    # User prompts
    language = Prompt.ask("Project language", choices=["python", "javascript", "java"], default=language)
    framework = Prompt.ask("Test framework", default=framework)
    
    config = {
        "language": language,
        "framework": framework,
        "confidence_threshold": 0.6,
        "auto_accept": False,
        "max_concurrency": 5,
        "exclude_patterns": [
            "node_modules", 
            "venv", 
            ".git", 
            "__pycache__", 
            "dist", 
            "build"
        ]
    }
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
        
    display.success(f"Initialized Code2Test configuration in {config_file}")
    display.info("Run 'code2test generate' to start generating tests!")
