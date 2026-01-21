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
from code2test.core.intent import IntentExtractor
from code2test.core.verifier import TestVerifier
from code2test.core.generator import TestGenerator

__all__ = [
    # Models
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
    # Core classes
    "IntentExtractor",
    "TestVerifier",
    "TestGenerator",
]
