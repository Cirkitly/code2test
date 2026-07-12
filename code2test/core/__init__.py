"""Code2Test Core Module.

Core functionality for intent-first test generation.

Import policy: this __init__ exposes models and stateless core classes
(IntentExtractor, TestVerifier) eagerly. TestGenerator is intentionally
NOT imported here -- it pulls in the agent trio and creates a partial
load hazard when pytest alphabetical discovery touches agents before
core. Import TestGenerator directly from code2test.core.generator if
you need it.
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
    # Core classes (stateless; safe to import eagerly)
    "IntentExtractor",
    "TestVerifier",
    # TestGenerator must be imported explicitly:
    #   from code2test.core.generator import TestGenerator
]  # noqa
