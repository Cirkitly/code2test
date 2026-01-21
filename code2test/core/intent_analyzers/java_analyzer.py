"""
Java intent analyzer.
"""

from typing import Dict, Any
from code2test.core.intent_analyzers.base_analyzer import IntentAnalyzer

class JavaAnalyzer(IntentAnalyzer):
    """Analyzer for Java code intents."""
    
    # Similar to JS but can be extended with Java-specific frameworks
    NAMING_PATTERNS = {
        r"^validate|^isValid|^check": "validation",
        r"^is|^has|^can|^should": "boolean check",
        r"^get|^fetch|^retrieve|^load": "data retrieval",
        r"^set|^update|^modify|^change": "data modification",
        r"^create|^make|^build|^generate|^factory": "creation/generation",
        r"^delete|^remove|^destroy|^clear": "deletion/removal",
        r"^parse|^extract|^split": "parsing/extraction",
        r"^format|^render|^display": "formatting/display",
        r"^save|^store|^persist|^write": "persistence",
        r"^find|^search|^lookup|^query": "search/lookup",
        r"^convert|^transform|^to[A-Z]": "conversion/transformation",
        r"^init|^initialize|^setup": "initialization",
        r"^handle|^process|^execute|^run": "processing/handling",
        r"^send|^emit|^dispatch|^publish": "sending/publishing",
        r"^on[A-Z]|^handle[A-Z]": "event handling",
        r"^auth|^login|^logout": "authentication/authorization",
        r"^test|^assert|^verify": "testing/verification",
    }

    def extract_docstring(self, component: Dict[str, Any]) -> str:
        """Extract Javadoc."""
        return component.get("docstring", "").strip()
        
    def extract_multiline_comment(self, component: Dict[str, Any]) -> str:
        return self.extract_docstring(component)

    def extract_signature(self, component: Dict[str, Any]) -> str:
        return component.get("signature", "")
        
    def extract_type_hints(self, component: Dict[str, Any]) -> str:
        """Extract Java type hints (inherent in signature)."""
        # Java signatures are strongly typed, so the signature itself is the type hint
        return component.get("signature", "")
        
    def get_naming_patterns(self) -> Dict[str, str]:
        return self.NAMING_PATTERNS
