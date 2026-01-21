"""
Intent command for Code2Test CLI.
"""

from pathlib import Path
from typing import Optional
import click
from rich.console import Console

from code2test.cli.display import DisplayManager
from code2test.cli.interactive import InteractiveSession

console = Console()


@click.command("intent")
@click.argument("action", type=click.Choice(["show", "edit", "export"]))
@click.argument("component", required=False)
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def intent_command(
    action: str,
    component: Optional[str],
    format: str
) -> None:
    """
    View or edit inferred intents.
    
    \b
    Examples:
        code2test intent show auth        # Show intents for auth module
        code2test intent edit validate    # Edit intent for validate function
        code2test intent export --format json  # Export all intents
    """
    display = DisplayManager()
    
    # Import storage
    from code2test.storage import IntentDatabase
    
    # Find database
    db_path = Path.cwd() / ".code2test" / "code2test.db"
    
    if not db_path.exists():
        display.error("No intent database found. Run 'code2test test' first.")
        return
    
    db = IntentDatabase(str(db_path))
    
    if action == "show":
        if component:
            intent = db.get_intent(component)
            if intent:
                display.show_intent(intent)
            else:
                display.warning(f"No intent found for: {component}")
        else:
            intents = db.get_all_intents()
            if intents:
                for intent in intents:
                    display.show_intent(intent)
            else:
                display.info("No intents stored yet.")
    
    elif action == "export":
        intents = db.get_all_intents()
        
        if format == "json":
            import json
            data = [i.model_dump() for i in intents]
            console.print(json.dumps(data, indent=2, default=str))
        else:
            for intent in intents:
                console.print(f"{intent.component_id}: {intent.intent_text}")
    
    elif action == "edit":
        if not component:
            display.error("Component name required for edit")
            return
        
        intent = db.get_intent(component)
        if not intent:
            display.error(f"No intent found for: {component}")
            return
        
        session = InteractiveSession(display)
        new_text = session.edit_intent(intent)
        
        if new_text != intent.intent_text:
            intent.update_intent(new_text)
            db.save_intent(intent)
            display.success("Intent updated")
