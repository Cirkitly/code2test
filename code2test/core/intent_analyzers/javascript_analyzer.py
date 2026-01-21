"""
JavaScript/TypeScript intent analyzer.
"""

from typing import Dict, Any
from code2test.core.intent_analyzers.base_analyzer import IntentAnalyzer

class JavascriptAnalyzer(IntentAnalyzer):
    """Analyzer for JavaScript/TypeScript code intents."""
    
    # Adapted patterns for camelCase
    NAMING_PATTERNS = {
        r"^validate|^isValid|^check": "validation",
        r"^is|^has|^can|^should": "boolean check",
        r"^get|^fetch|^retrieve|^load": "data retrieval",
        r"^set|^update|^modify|^change": "data modification",
        r"^create|^make|^build|^generate": "creation/generation",
        r"^delete|^remove|^destroy|^clear": "deletion/removal",
        r"^parse|^extract|^split": "parsing/extraction",
        r"^format|^render|^display": "formatting/display",
        r"^save|^store|^persist|^write": "persistence",
        r"^find|^search|^lookup|^query": "search/lookup",
        r"^convert|^transform|^to[A-Z]": "conversion/transformation",
        r"^init|^initialize|^setup": "initialization",
        r"^handle|^process|^execute": "processing/handling",
        r"^send|^emit|^dispatch|^publish": "sending/publishing",
        r"^receive|^consume|^subscribe": "receiving/consuming",
        r"^auth|^login|^logout": "authentication/authorization",
        r"^encrypt|^decrypt|^hash": "cryptography",
        r"^log|^debug": "logging/debugging",
        r"^test|^spec": "testing/verification",
    }

    def extract_docstring(self, component: Dict[str, Any]) -> str:
        """Extract JSDoc or leading comments."""
        # Assuming the component model normalizes 'docstring' field from JSDoc
        return component.get("docstring", "").strip()
        
    def extract_multiline_comment(self, component: Dict[str, Any]) -> str:
        return self.extract_docstring(component)

    def extract_signature(self, component: Dict[str, Any]) -> str:
        return component.get("signature", "")
        
    def extract_type_hints(self, component: Dict[str, Any]) -> str:
        """Extract TypeScript type annotations if present."""
        signature = component.get("signature", "")
        # TS usually has ': Type' pattern
        if ":" in signature or "=>" in signature:
            return signature
        return ""
        
    def get_naming_patterns(self) -> Dict[str, str]:
        return self.NAMING_PATTERNS
