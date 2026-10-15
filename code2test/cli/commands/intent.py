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
def intent_command(action: str, component: Optional[str], format: str) -> None:
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
            matches = _find_intents(db, component)
            for intent in matches:
                display.show_intent(intent)
            if not matches:
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
            # plain output: rich would wrap long lines and break the JSON
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            for intent in intents:
                click.echo(f"{intent.component_id}: {intent.intent_text}")

    elif action == "edit":
        if not component:
            display.error("Component name required for edit")
            return

        matches = _find_intents(db, component)
        if not matches:
            display.error(f"No intent found for: {component}")
            return
        if len(matches) > 1:
            display.error(f"'{component}' matches several components; use one of:")
            for m in matches:
                console.print(f"  {m.component_id}")
            return
        intent = matches[0]

        session = InteractiveSession(display)
        new_text = session.edit_intent(intent)

        if new_text != intent.intent_text:
            intent.update_intent(new_text)
            db.save_intent(intent)
            display.success("Intent updated")


def _find_intents(db, query: str) -> list:
    """
    Resolve a user-supplied name to intents.

    Tries, in order: the exact component id ("pkg.mod.func"), a short name
    ("func"), then a module or package prefix ("pkg.mod", "pkg").
    """
    exact = db.get_intent(query)
    if exact:
        return [exact]
    intents = db.get_all_intents()
    by_name = [i for i in intents if i.component_id.split(".")[-1] == query]
    if by_name:
        return by_name
    return [
        i
        for i in intents
        if i.component_id.startswith(query + ".") or f".{query}." in f".{i.component_id}"
    ]
