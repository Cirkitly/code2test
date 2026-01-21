"""
Code2Test Core Module

Core functionality for intent-first test generation.
"""

from code2test.core.models import (
    Intent,
    IntentEvidence,
    TestCase,
    TestFile,
    TestSuite,
    TestStatus,
    TestFramework,
    Diagnosis,
    DiagnosisCause,
    VerificationResult,
    GenerationConfig,
)

__all__ = [
    "Intent",
    "IntentEvidence",
    "TestCase",
    "TestFile",
    "TestSuite",
    "TestStatus",
    "TestFramework",
    "Diagnosis",
    "DiagnosisCause",
    "VerificationResult",
    "GenerationConfig",
]
