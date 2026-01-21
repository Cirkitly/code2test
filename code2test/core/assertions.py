"""
Assertion Pattern Library.

Provides a standardized way to generate assertions across different languages/frameworks.
"""

from typing import Any, Dict, Optional

class AssertionLibrary:
    """Library of assertion patterns for different frameworks."""
    
    PATTERNS = {
        "pytest": {
            "equal": "assert {actual} == {expected}",
            "not_equal": "assert {actual} != {expected}",
            "true": "assert {actual}",
            "false": "assert not {actual}",
            "raises": "with pytest.raises({expected}):\n    {actual}",
            "contains": "assert {expected} in {actual}",
            "is_none": "assert {actual} is None",
            "is_not_none": "assert {actual} is not None",
        },
        "jest": {
            "equal": "expect({actual}).toEqual({expected})",
            "not_equal": "expect({actual}).not.toEqual({expected})",
            "true": "expect({actual}).toBeTruthy()",
            "false": "expect({actual}).toBeFalsy()",
            "raises": "expect(() => {actual}).toThrow({expected})",
            "contains": "expect({actual}).toContain({expected})",
            "is_none": "expect({actual}).toBeNull()",
            "is_not_none": "expect({actual}).not.toBeNull()",
        },
        "junit": {
            "equal": "assertEquals({expected}, {actual});",
            "not_equal": "assertNotEquals({expected}, {actual});",
            "true": "assertTrue({actual});",
            "false": "assertFalse({actual});",
            "raises": "assertThrows({expected}.class, () -> {actual});",
            "contains": "assertTrue({actual}.contains({expected}));",
            "is_none": "assertNull({actual});",
            "is_not_none": "assertNotNull({actual});",
        }
    }
    
    @classmethod
    def get_assertion(cls, framework: str, type: str, actual: str, expected: str = "") -> str:
        """
        Get formatted assertion code.
        
        Args:
            framework: Test framework (pytest, jest, junit)
            type: Assertion type (equal, true, raises, etc.)
            actual: Actual value snippet
            expected: Expected value snippet (optional)
            
        Returns:
            Formatted assertion string
        """
        framework = framework.lower()
        if framework not in cls.PATTERNS:
            raise ValueError(f"Unknown framework: {framework}")
            
        patterns = cls.PATTERNS[framework]
        if type not in patterns:
            # Fallback to equality if unknown
            type = "equal"
            
        pattern = patterns[type]
        return pattern.format(actual=actual, expected=expected)
