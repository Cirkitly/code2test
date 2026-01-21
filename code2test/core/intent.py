"""
Code2Test Intent Extraction

Extracts behavioral intent from code components using multiple signals.
Delegates to language-specific analyzers.
"""

import re
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from code2test.core.models import Intent, IntentEvidence
from code2test.core.intent_analyzers import (
    IntentAnalyzer,
    PythonAnalyzer,
    JavascriptAnalyzer,
    JavaAnalyzer
)


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
        # Cache analyzers
        self._analyzers = {
            "python": PythonAnalyzer(),
            "javascript": JavascriptAnalyzer(),
            "typescript": JavascriptAnalyzer(),  # Re-use JS analyzer for TS
            "java": JavaAnalyzer(),
        }
        self._default_analyzer = PythonAnalyzer()
    
    def _get_analyzer(self, component: Dict[str, Any]) -> IntentAnalyzer:
        """Determine correct analyzer for component."""
        # Try explicit language field
        lang = component.get("language", "").lower()
        if lang in self._analyzers:
            return self._analyzers[lang]
            
        # Try file extension
        file_path = component.get("file_path", "")
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == ".py":
            return self._analyzers["python"]
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            return self._analyzers["javascript"]
        elif ext == ".java":
            return self._analyzers["java"]
            
        return self._default_analyzer
    
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
        
        analyzer = self._get_analyzer(component)
        
        # Extract all signals
        signals = self._extract_signals(component, dependency_intents, analyzer)
        
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
        dependency_intents: Dict[str, Intent],
        analyzer: IntentAnalyzer
    ) -> IntentSignals:
        """Extract all intent signals from component using analyzer."""
        signals = IntentSignals()
        
        # Docstring signal
        docstring = analyzer.extract_docstring(component)
        if docstring:
            signals.docstring = docstring
            # Higher weight for longer, more detailed docstrings
            doc_length = len(docstring.split())
            signals.docstring_weight = min(self.DOCSTRING_WEIGHT, 
                                           self.DOCSTRING_WEIGHT * (doc_length / 20))
        
        # Signature and type hints
        signature = analyzer.extract_signature(component)
        if signature:
            signals.signature = signature
            
            type_hints = analyzer.extract_type_hints(component)
            if type_hints:
                signals.type_hints = type_hints
                signals.type_hint_weight = self.TYPE_HINT_WEIGHT
        
        # Naming signals
        name = component.get("name", "")
        if name:
            naming_signals = self._analyze_naming(name, analyzer)
            if naming_signals:
                signals.naming_signals = naming_signals
                signals.naming_weight = self.NAMING_WEIGHT
        
        # Call site analysis (if available) - Language agnostic mostly
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
        
        # Add type hint information (Generic logic, might need refinement)
        if signals.type_hints:
            # Simple heuristic to avoid adding raw ugly signatures
            if len(signals.type_hints) < 50: 
                 # This logic was Python specific (->), we generalize it slightly or omit it if too complex
                 # For now, just append if it's short, as it gives clues
                 pass
        
        # Fallback
        if not parts:
            parts.append(f"{component_type.capitalize()} '{name}'")
        
        return ". ".join(parts)
    
    def _analyze_naming(self, name: str, analyzer: IntentAnalyzer) -> List[str]:
        """
        Analyze function/class name for behavioral hints.
        """
        signals = []
        # Name matching might depend on language case conventions, but regex usually handles this
        # or we normalize.
        name_lower = name if "_" in name else name # Python/snake_case check
        # For camelCase, splitting is harder without extra libs, but regex patterns like "^get" work
        
        patterns = analyzer.get_naming_patterns()
        
        for pattern, behavior in patterns.items():
            if re.search(pattern, name): # Use case-sensitive matching if pattern dictates, or flags
                 # Most patterns we defined don't use flags but rely on ^get vs ^Get or just lowercase in patterns
                 # Actually, patterns in my analyzers used ^get etc.
                 # Let's try case-insensitive search to be safe for mixed conventions
                 signals.append(behavior)
            elif re.search(pattern, name, re.IGNORECASE):
                 signals.append(behavior)
        
        # De-duplicate
        return list(set(signals))
    
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

