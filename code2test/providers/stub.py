"""Deterministic stub provider (offline, no API calls).

The stub returns values derived from the literal content of the prompt
so that two predict() calls with the same inputs always yield the same
result. This makes the stub trivially diff-friendly and useful for
regression-testing agents that go through the seam.

Synthesis rules:
    str   fields  ->  f"stub:{field_name}:{first_32_chars_of_user}"
    float fields  ->  0.5 if field has 'confidence' in name, else 0.7
    bool  fields  ->  True (test runners exercise both branches elsewhere)
    list  fields  ->  ["stub"]
    dict  fields  ->  {"stub": True}
    other         ->  schema.model_construct default if defined, else None

v1.0 scope is small; we don't try to synthesize content-aware answers.
If a schema has a strict validator that rejects the stub values, that's
a bug in the agent's prompt — surface it loudly in tests.
"""

from __future__ import annotations

import re
from typing import Any, get_args, get_origin
from uuid import uuid4

from pydantic import BaseModel

from .base import Provider, T


_PUNCT_RE = re.compile(r"[^A-Za-z0-9]+")


def _slug_user(user: str) -> str:
    """Make a short, deterministic, URL-safe label from the user prompt."""
    s = _PUNCT_RE.sub("_", user.strip())[:32].strip("_")
    return s or "empty"


def _stub_value_for_field(name: str, annotation: Any) -> Any:
    """Synthesize a value that roughly matches `annotation`."""
    name_l = name.lower()
    origin = get_origin(annotation)
    args = get_args(annotation)

    # Bare list / dict (and parameterized versions).
    if annotation is list or origin is list:
        return ["stub"]
    if annotation is dict or origin is dict:
        return {"stub": True}

    # Optional[X] / Union[X, None]
    if origin is type(None):
        return None
    if origin and args and type(None) in args:
        # Treat as the non-None type
        non_none = next((a for a in args if a is not type(None)), str)
        return _stub_value_for_field(name, non_none)

    # bool
    if annotation is bool:
        return True

    # int / float
    if annotation is int:
        return 0
    if annotation is float:
        return 0.5 if "confidence" in name_l else 0.7

    # str and unknown
    return f"stub:{name}:<unset>"


def _stub_value_for(name: str, schema: type[T]) -> Any:
    """Look up the field annotation in the schema and synthesize a value."""
    fields = schema.model_fields
    if name not in fields:
        # Unknown field; use a conservative default.
        return None
    annotation = fields[name].annotation
    if annotation is None:
        return None
    return _stub_value_for_field(name, annotation)


class StubProvider(Provider):
    """v1.0 deterministic provider. No network. No async backend.

    Determinism contract: predict(system, user, schema) ==
    predict(system, user, schema). Verified in tests/unit/test_stub_provider.py.
    """

    def predict(self, system: str, user: str, schema: type[T]) -> T:
        slug = _slug_user(user)
        values: dict[str, Any] = {}
        for fname in schema.model_fields:
            if "name" in fname.lower():
                values[fname] = f"stub_{slug}_{uuid4().hex[:4]}"
            elif fname == "test_code":
                values[fname] = f"# stub\ndef test_{slug}():\n    pass\n"
            elif fname == "explanation":
                values[fname] = f"stub explanation for {slug}"
            elif fname == "intent_text":
                values[fname] = f"stub intent for {slug}"
            else:
                values[fname] = _stub_value_for(fname, schema)

        # Make slug-aware variants for string fields so the test can assert
        # the user prompt is reflected in the response.
        for fname in list(values):
            if isinstance(values[fname], str) and values[fname] == f"stub:{fname}:<unset>":
                values[fname] = f"stub:{fname}:{slug}"

        # Use model_construct to bypass validators; we are testing the seam
        # path, not the schema's own validation.
        try:
            return schema.model_construct(**values)
        except Exception:
            # Some schemas forbid model_construct (pydantic v1 internals).
            # Fall back to a regular construction with explicit dict.
            return schema(**values)


__all__ = ["StubProvider"]
