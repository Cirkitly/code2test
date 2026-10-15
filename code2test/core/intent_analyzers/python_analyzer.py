"""
Python-specific intent analyzer.
"""

import ast
import textwrap
from typing import Any, Dict, Optional
from code2test.core.intent_analyzers.base_analyzer import IntentAnalyzer

class PythonAnalyzer(IntentAnalyzer):
    """Analyzer for Python code intents."""
    
    NAMING_PATTERNS = {
        r"^validate_|^is_valid_|^check_": "validation",
        r"^is_|^has_|^can_|^should_": "boolean check",
        r"^get_|^fetch_|^retrieve_|^load_": "data retrieval",
        r"^set_|^update_|^modify_|^change_": "data modification",
        r"^create_|^make_|^build_|^generate_": "creation/generation",
        r"^delete_|^remove_|^destroy_|^clear_": "deletion/removal",
        r"^parse_|^extract_|^split_": "parsing/extraction",
        r"^format_|^render_|^display_": "formatting/display",
        r"^save_|^store_|^persist_|^write_": "persistence",
        r"^find_|^search_|^lookup_|^query_": "search/lookup",
        r"^convert_|^transform_|^to_": "conversion/transformation",
        r"^init_|^initialize_|^setup_": "initialization",
        r"^handle_|^process_|^execute_": "processing/handling",
        r"^send_|^emit_|^dispatch_|^publish_": "sending/publishing",
        r"^receive_|^consume_|^subscribe_": "receiving/consuming",
        r"^auth_|^authenticate_|^authorize_": "authentication/authorization",
        r"^encrypt_|^decrypt_|^hash_": "cryptography",
        r"^log_|^trace_|^debug_": "logging/debugging",
        r"^test_|^assert_|^verify_": "testing/verification",
        r"^main$|^run$|^cli$|^app$": "application entry point",
    }

    def extract_docstring(self, component: Dict[str, Any]) -> str:
        """Extract Python docstring."""
        return (component.get("docstring") or "").strip()

    def extract_multiline_comment(self, component: Dict[str, Any]) -> str:
        """Extract multiline comments (usually same as docstring in Python models)."""
        return self.extract_docstring(component)

    def extract_signature(self, component: Dict[str, Any]) -> str:
        """
        Extract the Python signature, e.g. ``def add(a: int, b: int) -> int``.

        Uses the ``signature`` field when present, otherwise parses the header
        of the component's source code (the dependency analyzer only stores source).
        """
        if component.get("signature"):
            return component["signature"]
        node = self._parse_definition(component)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            return f"{prefix} {node.name}({ast.unparse(node.args)}){returns}"
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            return f"class {node.name}({bases})" if bases else f"class {node.name}"
        return ""

    def extract_type_hints(self, component: Dict[str, Any]) -> str:
        """Return the signature if it carries type annotations, else an empty string."""
        node = self._parse_definition(component)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = args.posonlyargs + args.args + args.kwonlyargs + [a for a in (args.vararg, args.kwarg) if a]
            annotated = node.returns is not None or any(a.annotation is not None for a in all_args)
            return self.extract_signature(component) if annotated else ""
        if isinstance(node, ast.ClassDef):
            return ""
        signature = component.get("signature") or ""
        if "->" in signature or ": " in signature:
            return signature
        return ""

    @staticmethod
    def _parse_definition(component: Dict[str, Any]) -> Optional[ast.AST]:
        """The first top-level def/class in the component's source, if it parses."""
        source = component.get("source_code") or ""
        try:
            tree = ast.parse(textwrap.dedent(source))
        except (SyntaxError, ValueError):
            return None
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return node
        return None

    def get_naming_patterns(self) -> Dict[str, str]:
        return self.NAMING_PATTERNS
