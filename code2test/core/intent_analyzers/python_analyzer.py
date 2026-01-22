"""
Python-specific intent analyzer.
"""

from typing import Dict, Any
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
        return component.get("docstring", "").strip()
        
    def extract_multiline_comment(self, component: Dict[str, Any]) -> str:
        """Extract multiline comments (usually same as docstring in Python models)."""
        return self.extract_docstring(component)

    def extract_signature(self, component: Dict[str, Any]) -> str:
        """Extract Python signature."""
        return component.get("signature", "")
        
    def extract_type_hints(self, component: Dict[str, Any]) -> str:
        """Extract Python type hints from signature."""
        signature = component.get("signature", "")
        # Simple extraction logic from original intent.py
        # In a real AST walk we would have structured type info, but here we parse the string
        if "->" in signature or ": " in signature:
            return signature
        return ""
        
    def get_naming_patterns(self) -> Dict[str, str]:
        return self.NAMING_PATTERNS
