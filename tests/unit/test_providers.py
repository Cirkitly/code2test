"""Tests for the M1A.2 provider seam.

Covers:
    1. StubProvider.predict is deterministic for the same inputs.
    2. StubProvider honors schema field types (str, float, list, bool).
    3. StubProvider returns a fully-constructed pydantic instance.
    4. get_provider dispatches "stub" to StubProvider.
    5. get_provider raises NotImplementedError-free ValueError on unknown.
    6. PydanticAIProvider.predict raises NotImplementedError (v1.0).
    7. End-to-end: get_provider returns a Provider, .predict() works.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from code2test.config import Config
from code2test.providers import get_provider, StubProvider, Provider
from code2test.providers.pydantic_ai_provider import PydanticAIProvider


class Out(BaseModel):
    intent_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    tags: list = Field(default_factory=list)
    flagged: bool = False


class StrictOut(BaseModel):
    """A schema that demands the confidence field be in [0, 1]."""
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


def test_stub_is_deterministic():
    p = StubProvider()
    a = p.predict("sys", "user-input", Out)
    b = p.predict("sys", "user-input", Out)
    # Determinism contract: same inputs -> same outputs.
    assert a == b
    assert a.intent_text == b.intent_text


def test_stub_returns_constructed_instance():
    p = StubProvider()
    out = p.predict("sys", "anything", Out)
    assert isinstance(out, Out)
    assert isinstance(out.intent_text, str) and out.intent_text
    assert 0.0 <= out.confidence <= 1.0
    assert isinstance(out.tags, list)


def test_stub_confidence_field_recognizes_name():
    """confidence fields get 0.5; float fields without 'confidence' get 0.7."""
    class HasConfidence(BaseModel):
        confidence: float
    class HasOtherFloat(BaseModel):
        score: float
    p = StubProvider()
    a = p.predict("sys", "x", HasConfidence)
    b = p.predict("sys", "x", HasOtherFloat)
    assert a.confidence == pytest.approx(0.5)
    assert b.score == pytest.approx(0.7)


def test_stub_handles_strict_validators():
    p = StubProvider()
    out = p.predict("sys", "user", StrictOut)
    assert isinstance(out, StrictOut)
    assert 0.0 <= out.confidence <= 1.0


def test_get_provider_dispatches_stub():
    cfg = Config(provider="stub")
    p = get_provider(cfg)
    assert isinstance(p, StubProvider)
    assert isinstance(p, Provider)


def test_get_provider_dispatches_openai_returns_pydantic_ai_provider():
    cfg = Config(provider="openai", model="x", base_url="http://x", api_key="k")
    p = get_provider(cfg)
    assert isinstance(p, PydanticAIProvider)


def test_get_provider_dispatches_pydantic_ai_alias():
    cfg = Config(provider="pydantic-ai", model="x")
    p = get_provider(cfg)
    assert isinstance(p, PydanticAIProvider)


def test_get_provider_unknown_raises_value_error():
    cfg = Config(provider="made-up-thing")
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider(cfg)


def test_pydantic_ai_provider_predict_raises_not_implemented():
    p = PydanticAIProvider(model_name="x", base_url="http://x", api_key="k")
    with pytest.raises(NotImplementedError, match="v1.0"):
        p.predict("sys", "user", Out)


def test_provider_protocol_satisfied():
    """A Provider without predict() must produce NotImplementedError, not
    a different exception, so callers know it's an unfinished implementation.
    """
    class Empty(Provider):
        pass
    with pytest.raises(NotImplementedError):
        Empty().predict("sys", "user", Out)
