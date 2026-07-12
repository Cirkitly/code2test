"""Generate an OpenAI-SDK-strict JSON schema from a pydantic BaseModel.

The openai SDK accepts ``response_format={"type": "json_schema",
"json_schema": {...}}``. The contained ``json_schema`` must be
strict-compliant (every object schema must set
``additionalProperties: false`` and every ``array`` must declare its
items schema). Pydantic 2 emits a permissive shape by default; this
helper walks the schema and adds the bits the openai SDK complains
about.

The function works recursively and mutates in place. Returns the same
dict for convenience.
"""
from __future__ import annotations

from typing import Any, Dict


def _set_additional_false(node: Any, defs: Dict[str, Any] | None = None) -> None:
    """Recursively ensure every object-like schema sets
    ``additionalProperties: false``.

    Pass 1: walk the document, set the flag on every inline object
    schema. ``defs`` is passed only when we're descending a $ref
    resolution.

    Pass 2: same flag applied to every definition under $defs so that
    schemas referenced via ``$ref`` are also compliant.
    """
    if not isinstance(node, dict):
        return

    # If this is a $ref, resolve to the definition and stop. Don't
    # recurse into the same walk (the definitions are walked separately
    # in pass 2).
    if "$ref" in node and defs is not None:
        ref = node["$ref"]
        target_name = None
        if ref.startswith("#/$defs/"):
            target_name = ref[len("#/$defs/"):]
        elif ref.startswith("#//"):
            target_name = ref[len("#//"):]
        if target_name and target_name in defs:
            target = defs[target_name]
            if isinstance(target, dict):
                _ensure_ap_false(target)
        return

    # OpenAI strict JSON-schema requires this on every object schema.
    _ensure_ap_false(node)

    for child in node.values():
        if isinstance(child, dict):
            _set_additional_false(child, defs)
        elif isinstance(child, list):
            for item in child:
                _set_additional_false(item, defs)


def _ensure_ap_false(node: Dict[str, Any]) -> None:
    """Set ``additionalProperties: false`` on this node if it's an object
    schema and the flag isn't already present.
    """
    if node.get("type") == "object" or "properties" in node:
        if node.get("additionalProperties") is None:
            node["additionalProperties"] = False


def _walk_defs(node: Dict[str, Any]) -> None:
    """Apply ``additionalProperties: false`` to every definition.

    $defs can appear at any depth. We walk them.
    """
    defs = node.get("$defs")
    if isinstance(defs, dict):
        for _, schema_def in defs.items():
            if isinstance(schema_def, dict):
                _ensure_ap_false(schema_def)
                # Recurse so nested definitions inside other definitions
                # are also covered.
                _walk_defs(schema_def)


def pydantic_to_openai_strict_schema(pyd_model: type) -> Dict[str, Any]:
    """Return an openai-SDK-compatible strict JSON schema for ``pyd_model``.

    Two passes:
      1. Walk the document tree (no $defs) and set
         additionalProperties: false on every inline object schema.
      2. Walk every $defs entry and apply the same flag so that
         referenced definitions are also compliant.
    """
    schema = pyd_model.model_json_schema(ref_template="#/$defs/{model}")
    _set_additional_false(schema)
    _walk_defs(schema)
    return schema


def openai_response_format(pyd_model: type, name: str) -> Dict[str, Any]:
    """Return a ``response_format`` dict ready for openai.chat.completions.

    The openai SDK accepts this shape on ``chat.completions.create`` even
    though the typed surface doesn't enumerate the JSON-schema variant;
    runtime validation does. Returns a dict with the strict-true wrapper
    so the SDK or the server enforces structure.
    """
    schema = pydantic_to_openai_strict_schema(pyd_model)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }


__all__ = [
    "pydantic_to_openai_strict_schema",
    "openai_response_format",
]
