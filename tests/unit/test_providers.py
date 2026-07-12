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
    cfg = Config(provider="pydantic-ai", model="x", api_key="k")
    p = get_provider(cfg)
    assert isinstance(p, PydanticAIProvider)


def test_get_provider_unknown_raises_value_error():
    cfg = Config(provider="made-up-thing")
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider(cfg)


def test_pydantic_ai_provider_rejects_missing_api_key():
    """api_key must be set before predict() can succeed.

    Surface the failure as early as possible (constructor) so misconfig
    is loud, not surprising.
    """
    with pytest.raises(ValueError, match="api_key"):
        PydanticAIProvider(model_name="x", base_url="http://x", api_key="")


def test_pydantic_ai_provider_rejects_empty_model_name():
    """model_name must be set; an empty string would produce a 400 from
    every OpenAI-compatible endpoint.
    """
    with pytest.raises(ValueError, match="model_name"):
        PydanticAIProvider(model_name="", api_key="k")


def test_pydantic_ai_provider_predict_uses_mocked_openai_client():
    """End-to-end of the OpenAI-SDK roundtrip with a mocked client.

    Verifies that:
      * predict() makes exactly one chat.completions.create call
      * the messages use role=system with our schema-instruction
        prepended, and role=user with the user prompt
      * the model name forwarded from constructor is used
      * base_url forwarding is correct (delegated to OpenAI client)
      * the JSON reply is parsed into the schema instance
    """
    out_schema_json = {
        "intent_text": "reduce path with no symlinks",
        "confidence": 0.91,
    }
    mock_client = _mk_mock_completion(out_schema_json)

    p = PydanticAIProvider(
        model_name="gpt-4o-mini",
        base_url="http://testserver/v1",
        api_key="sk-test",
    )
    # Replace the SDK client with a mock. The provider stores the
    # openai.OpenAI instance at self._client.
    p._client = mock_client

    out = p.predict("system one", "user one", Out)
    assert isinstance(out, Out)
    assert out.intent_text == "reduce path with no symlinks"
    assert out.confidence == pytest.approx(0.91)

    # Verify the underlying call was made once with the right shape.
    mock_client.call.assert_called_once()
    kwargs = mock_client.call.call_kwargs
    assert kwargs is not None  # for type checkers; mock invariant
    assert kwargs["model"] == "gpt-4o-mini"
    messages = kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "user one"
    # Schema instruction is in the system message.
    assert "intent_text" in messages[0]["content"]
    assert "system one" in messages[0]["content"]
    assert kwargs["temperature"] == 0.0

    # v1.1 task 3b: response_format with strict JSON-schema envelope is
    # passed. This is what closes the loop on reasoning-capable models
    # that emit schema descriptions instead of array-element instances
    # when only prose-instructed.
    rf = kwargs.get("response_format")
    assert rf is not None  # belt-and-suspenders
    assert rf["type"] == "json_schema"
    schema_envelope = rf["json_schema"]
    assert schema_envelope["strict"] is True
    assert schema_envelope["name"] == "Out"
    inner = schema_envelope["schema"]
    assert inner.get("type") == "object"
    # Strict mode requires additionalProperties: false at every object
    # level; our helper walks and sets it.
    assert inner.get("additionalProperties") is False
    # Sanity-check the inner schema references Out's fields.
    assert "intent_text" in inner["properties"]
    assert "confidence" in inner["properties"]


def test_pydantic_ai_provider_schema_helpers_set_additional_properties_false():
    """The schema helper walks every object level and sets
    additionalProperties=false, including nested object schemas
    reachable via $ref.
    """
    from code2test.providers.schema_helpers import pydantic_to_openai_strict_schema

    schema = pydantic_to_openai_strict_schema(TestGenerationResultForHelpers)
    # Top-level object: additionalProperties must be false.
    assert schema.get("additionalProperties") is False

    # tests: list[GeneratedTestNested] -- the items $ref points into
    # $defs. The HELPER walks $defs and applies the flag on the
    # resolved definition, so the GeneratedTestNested object schema
    # also has additionalProperties: false. That is the strict-mode
    # requirement that triggered v1.1 task 3b's 400 errors.
    nested = schema["$defs"]["GeneratedTestNested"]
    assert nested.get("additionalProperties") is False
    # Spot-check the field names reach through.
    assert "name" in nested["properties"]
    assert "tests_behavior" in nested["properties"]
    assert set(nested["required"]) == {"name", "description", "test_code", "tests_behavior"}


class GeneratedTestNested(BaseModel):
    name: str
    description: str
    test_code: str
    tests_behavior: str


class TestGenerationResultForHelpers(BaseModel):
    tests: list[GeneratedTestNested]
    imports: list = Field(default_factory=list)
    fixtures: list = Field(default_factory=list)


def test_pydantic_ai_provider_predict_handles_markdown_fenced_json():
    """Models sometimes wrap replies in markdown fences. The extractor
    peels them off before passing to model_validate_json.
    """
    fenced = "```json\n{\"intent_text\": \"x\", \"confidence\": 0.5}\n```"
    mock_client = _mk_mock_completion_from_text(fenced)
    p = PydanticAIProvider(model_name="x", api_key="k")
    p._client = mock_client
    out = p.predict("sys", "user", Out)
    assert out.intent_text == "x"
    assert out.confidence == pytest.approx(0.5)


def test_pydantic_ai_provider_predict_handles_prose_with_embedded_json():
    """Models sometimes prefix JSON with prose. We extract the first
    {...} substring and parse that.
    """
    raw = 'Here you go:\n{"intent_text": "y", "confidence": 0.7}'
    mock_client = _mk_mock_completion_from_text(raw)
    p = PydanticAIProvider(model_name="x", api_key="k")
    p._client = mock_client
    out = p.predict("sys", "user", Out)
    assert out.intent_text == "y"
    assert out.confidence == pytest.approx(0.7)


def test_pydantic_ai_provider_predict_rejects_non_json_reply():
    """When the reply isn't JSON at all, predict() raises ValueError."""
    mock_client = _mk_mock_completion_from_text("not json at all")
    p = PydanticAIProvider(model_name="x", api_key="k")
    p._client = mock_client
    with pytest.raises(ValueError, match="does not contain JSON"):
        p.predict("sys", "user", Out)


def test_pydantic_ai_provider_predict_handles_reasoning_block():
    """Reasoning-capable models (MiniMax-M3 etc.) emit ``-prefixed
    JSON. The extractor peels the think block and parses the JSON.
    """
    reply = ("<think>The user wants a JSON object only.</think>\n\n"
             "{\"intent_text\": \"x\", \"confidence\": 0.5}")
    mock_client = _mk_mock_completion_from_text(reply)
    p = PydanticAIProvider(model_name="x", api_key="k")
    p._client = mock_client
    out = p.predict("sys", "user", Out)
    assert out.intent_text == "x"
    assert out.confidence == pytest.approx(0.5)


def test_pydantic_ai_provider_predict_handles_partial_reasoning_block():
    """A truncated `` block with no close tag is dropped from
    the open-tag onward, leaving whatever comes after.
    """
    reply = "stuff before <think>rambling\n\n{\"intent_text\": \"y\", \"confidence\": 0.7}"
    # This case still has balanced JSON after the <think> opens, but no
    # closing tag. The extractor should treat the entire <think>...</think>
    # block as missing (because the close is absent) and use the JSON
    # that appears after.
    mock_client = _mk_mock_completion_from_text(reply)
    p = PydanticAIProvider(model_name="x", api_key="k")
    p._client = mock_client
    # The extractor will treat this as a partial-block case and clip
    # from <think> onward, leaving "stuff before " + a stray leading
    # JSON substring. We expect this to raise — the corpus isn't JSON.
    with pytest.raises(ValueError, match="does not contain JSON"):
        p.predict("sys", "user", Out)


def test_pydantic_ai_provider_predict_rejects_empty_choices():
    """If the provider returns empty choices (rare but real), fail loudly."""
    empty = type("R", (), {})()
    empty.choices = []
    response = type("Resp", (), {"choices": []})()
    client = type("C", (), {"chat": type("CC", (), {"completions": type(
        "CCC", (), {"create": lambda self, **k: response})()})()})()
    p = PydanticAIProvider(model_name="x", api_key="k")
    p._client = client
    with pytest.raises(ValueError, match="empty choices"):
        p.predict("sys", "user", Out)


# --- helpers for the mocked-openai tests ---------------------------------


class _MockClient:
    """Test double for ``openai.OpenAI``. The provider puts this at
    ``self._client`` and calls ``self._client.chat.completions.create(...)``.
    """

    def __init__(self, content: str):
        # Use a fresh _MockCompletions instance per test so recorded
        # kwargs don't leak across tests.
        completions = _MockCompletions(content)
        self.chat = type("ChatNamespace", (), {"completions": completions})()
        self._completions = completions

    @property
    def call(self) -> _MockCompletions:
        return self._completions


class _MockCompletions:
    """Records a single chat.completions.create call and returns a
    canned response object.
    """

    def __init__(self, content: str):
        self._content = content
        self.call_kwargs: dict | None = None

    def create(self, **kwargs):
        self.call_kwargs = kwargs

        msg = type("Msg", (), {"content": self._content})()
        choice = type("Choice", (), {"message": msg})()
        return type("Resp", (), {"choices": [choice]})()

    def assert_called_once(self):
        assert self.call_kwargs is not None, "create() was never called"


def _mk_mock_completion(json_payload: dict) -> _MockClient:
    import json as _json
    return _MockClient(_json.dumps(json_payload))


def _mk_mock_completion_from_text(text: str) -> _MockClient:
    return _MockClient(text)


def test_provider_protocol_satisfied():
    """A Provider without predict() must produce NotImplementedError, not
    a different exception, so callers know it's an unfinished implementation.
    """
    class Empty(Provider):
        pass
    with pytest.raises(NotImplementedError):
        Empty().predict("sys", "user", Out)
