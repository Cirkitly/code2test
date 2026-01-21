"""
Code2Test Storage Module

Persistence layer for intents and generated tests.
"""

from code2test.storage.intent_db import IntentDatabase
from code2test.storage.test_registry import TestRegistry

__all__ = [
    "IntentDatabase",
    "TestRegistry",
]
