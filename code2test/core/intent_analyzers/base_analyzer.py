"""
Base interface for language-specific intent analyzers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from code2test.core.models import IntentEvidence

class IntentAnalyzer(ABC):
    """Abstract base class for language-specific intent analysis."""
    
    @abstractmethod
    def extract_docstring(self, component: Dict[str, Any]) -> str:
        """Extract docstring/comment block from component."""
        pass
        
    @abstractmethod
    def extract_multiline_comment(self, component: Dict[str, Any]) -> str:
        """Extract multiline comment from component."""
        pass

    @abstractmethod
    def extract_signature(self, component: Dict[str, Any]) -> str:
        """Extract function/method signature."""
        pass
        
    @abstractmethod
    def extract_type_hints(self, component: Dict[str, Any]) -> str:
        """Extract type information."""
        pass
        
    @abstractmethod
    def get_naming_patterns(self) -> Dict[str, str]:
        """Get regex patterns for naming convention analysis."""
        pass
