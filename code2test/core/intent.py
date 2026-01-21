"""
Code2Test Intent Extraction

Extracts behavioral intent from code components using multiple signals.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from code2test.core.models import Intent, IntentEvidence


# Naming pattern heuristics for common function behaviors
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
}


@dataclass
class IntentSignals:
    """Raw signals extracted from code for intent inference."""
    docstring: Optional[str] = None
    docstring_weight: float = 0.0
    signature: Optional[str] = None
    type_hints: Optional[str] = None
    type_hint_weight: float = 0.0
    naming_signals: List[str] = None
    naming_weight: float = 0.0
    call_sites: List[str] = None
    call_site_weight: float = 0.0
    complexity_penalty: float = 0.0
    
    def __post_init__(self):
        if self.naming_signals is None:
            self.naming_signals = []
        if self.call_sites is None:
            self.call_sites = []


class IntentExtractor:
    """
    Extracts behavioral intent from code components.
    
    Uses multiple signals to infer what code is supposed to do:
    - Docstrings and comments
    - Function signatures and type hints
    - Naming conventions
    - Call site analysis
    - Dependency intents
    """
    
    # Weight configuration (from proposal Appendix B)
    CONFIDENCE_BASE = 0.5
    DOCSTRING_WEIGHT = 0.30
    TYPE_HINT_WEIGHT = 0.20
    NAMING_WEIGHT = 0.15
    CALL_SITE_WEIGHT = 0.20
    DEPENDENCY_WEIGHT = 0.15
    MAGIC_NUMBER_PENALTY = 0.10
    COMPLEXITY_PENALTY = 0.15
    
    def __init__(self, confidence_threshold: float = 0.6):
        """
        Initialize intent extractor.
        
        Args:
            confidence_threshold: Minimum confidence for auto-acceptance
        """
        self.confidence_threshold = confidence_threshold
    
    def extract_intent(
        self,
        component: Dict[str, Any],
        dependency_intents: Optional[Dict[str, Intent]] = None
    ) -> Intent:
        """
        Extract intent from a code component.
        
        Args:
            component: Component data from AST analysis
            dependency_intents: Intents of dependencies for context
            
        Returns:
            Inferred Intent with confidence score
        """
        if dependency_intents is None:
            dependency_intents = {}
        
        # Extract all signals
        signals = self._extract_signals(component, dependency_intents)
        
        # Calculate confidence
        confidence = self._calculate_confidence(signals)
        
        # Generate intent text
        intent_text = self._generate_intent_text(component, signals)
        
        # Build evidence
        evidence = IntentEvidence(
            docstring=signals.docstring,
            signature=signals.signature,
            type_hints=signals.type_hints,
            naming_signals=signals.naming_signals,
            call_sites=signals.call_sites,
            dependency_intents=[
                f"{k}: {v.intent_text}" 
                for k, v in dependency_intents.items()
            ][:5],  # Limit to 5
        )
        
        return Intent(
            component_id=component.get("id", component.get("name", "unknown")),
            component_path=component.get("file_path", ""),
            intent_text=intent_text,
            confidence=confidence,
            evidence=evidence,
        )
    
    def _extract_signals(
        self,
        component: Dict[str, Any],
        dependency_intents: Dict[str, Intent]
    ) -> IntentSignals:
        """Extract all intent signals from component."""
        signals = IntentSignals()
        
        # Docstring signal
        docstring = component.get("docstring", "")
        if docstring:
            signals.docstring = docstring.strip()
            # Higher weight for longer, more detailed docstrings
            doc_length = len(docstring.split())
            signals.docstring_weight = min(self.DOCSTRING_WEIGHT, 
                                           self.DOCSTRING_WEIGHT * (doc_length / 20))
        
        # Signature and type hints
        signature = component.get("signature", "")
        if signature:
            signals.signature = signature
            
            # Check for type hints in signature
            if "->" in signature or ": " in signature:
                signals.type_hints = self._extract_type_hints(signature)
                signals.type_hint_weight = self.TYPE_HINT_WEIGHT
        
        # Naming signals
        name = component.get("name", "")
        if name:
            naming_signals = self._analyze_naming(name)
            if naming_signals:
                signals.naming_signals = naming_signals
                signals.naming_weight = self.NAMING_WEIGHT
        
        # Call site analysis (if available)
        call_sites = component.get("called_by", [])
        if call_sites:
            signals.call_sites = call_sites[:5]  # Limit to 5
            signals.call_site_weight = min(self.CALL_SITE_WEIGHT,
                                           self.CALL_SITE_WEIGHT * len(call_sites) / 3)
        
        # Complexity penalty
        complexity = component.get("cyclomatic_complexity", 1)
        if complexity > 10:
            signals.complexity_penalty = self.COMPLEXITY_PENALTY
        elif complexity > 5:
            signals.complexity_penalty = self.COMPLEXITY_PENALTY * 0.5
        
        return signals
    
    def _calculate_confidence(self, signals: IntentSignals) -> float:
        """Calculate confidence score from signals."""
        confidence = self.CONFIDENCE_BASE
        
        # Positive signals
        confidence += signals.docstring_weight
        confidence += signals.type_hint_weight
        confidence += signals.naming_weight
        confidence += signals.call_site_weight
        
        # Penalties
        confidence -= signals.complexity_penalty
        
        # Clamp to valid range
        return max(0.1, min(0.99, confidence))
    
    def _generate_intent_text(
        self,
        component: Dict[str, Any],
        signals: IntentSignals
    ) -> str:
        """Generate human-readable intent text."""
        parts = []
        
        name = component.get("name", "unknown")
        component_type = component.get("type", "function")
        
        # Start with docstring if available
        if signals.docstring:
            # Extract first sentence
            first_sentence = signals.docstring.split('.')[0].strip()
            if first_sentence:
                parts.append(first_sentence)
        
        # Add naming-based intent
        if signals.naming_signals and not parts:
            behavior = signals.naming_signals[0]
            parts.append(f"Performs {behavior} operation")
        
        # Add type hint information
        if signals.type_hints and "->" in signals.type_hints:
            return_type = signals.type_hints.split("->")[-1].strip()
            if return_type and return_type != "None":
                parts.append(f"Returns {return_type}")
        
        # Fallback
        if not parts:
            parts.append(f"{component_type.capitalize()} '{name}'")
        
        return ". ".join(parts)
    
    def _extract_type_hints(self, signature: str) -> str:
        """Extract type hints from function signature."""
        # Simple extraction - could be enhanced
        return signature
    
    def _analyze_naming(self, name: str) -> List[str]:
        """
        Analyze function/class name for behavioral hints.
        
        Args:
            name: Function or class name
            
        Returns:
            List of inferred behaviors from naming
        """
        signals = []
        name_lower = name.lower()
        
        for pattern, behavior in NAMING_PATTERNS.items():
            if re.search(pattern, name_lower):
                signals.append(behavior)
        
        return signals
    
    def needs_clarification(self, intent: Intent) -> bool:
        """Check if intent needs user clarification."""
        return intent.confidence < self.confidence_threshold
    
    def get_clarification_questions(self, intent: Intent, component: Dict[str, Any]) -> List[str]:
        """
        Generate clarification questions for low-confidence intent.
        
        Args:
            intent: The low-confidence intent
            component: Component data
            
        Returns:
            List of questions to ask the user
        """
        questions = []
        name = component.get("name", "unknown")
        
        # Check what evidence is missing
        if not intent.evidence.docstring:
            questions.append(f"What is the primary purpose of '{name}'?")
        
        if not intent.evidence.type_hints:
            questions.append(f"What types of inputs does '{name}' accept and what does it return?")
        
        # Check for complex behavior
        if component.get("cyclomatic_complexity", 1) > 5:
            questions.append(f"'{name}' has complex logic. What are the main scenarios it handles?")
        
        # Check for error handling
        if "exception" in str(component).lower() or "error" in str(component).lower():
            questions.append(f"What error conditions should '{name}' handle?")
        
        # Default question
        if not questions:
            questions.append(f"Please describe the expected behavior of '{name}'.")
        
        return questions
