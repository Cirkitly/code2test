"""Provider backed by the OpenAI SDK.

The class name ``PydanticAIProvider`` is preserved for backward
compatibility with v1.0 imports; semantically this is an
OpenAI-compatible provider. It speaks the OpenAI Chat Completions
HTTP shape, which means every endpoint that clones that shape —

* OpenAI (api.openai.com)
* minimax (api.minimax.io/v1, the project's v1.1 deployment target)
* Anthropic's OpenAI-compatible bridge
* Locally-hosted OpenAI-compatible servers (vLLM, Ollama, etc.)

works without vendor-specific branches. **No ``if minimax:`` or any
other vendor check lives in this file.** The only knobs are
``base_url``, ``api_key``, and ``model_name``; all three are read from
``Config`` and default to env-var values set by the operator.

Strictly synchronous: predict() returns a constructed schema
instance. The seam contract is sync (apredict is provided by the
base class and forwards to predict).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from .base import Provider, T

logger = logging.getLogger(__name__)


class PydanticAIProvider(Provider):
    """OpenAI-SDK-backed provider. Backend-agnostic by construction.

    The class wraps the official ``openai.OpenAI`` synchronous client.
    Callers pass ``model_name``, ``base_url``, and ``api_key`` at
    construction; the OpenAI client is built once and reused for every
    ``predict()`` call so connection pooling works correctly across the
    agent's three call sites (intent, test, diagnosis).

    The mapping from ``Config`` to ``PydanticAIProvider`` lives in
    :func:`code2test.providers.get_provider` and the seam is documented
    there. This module deliberately does not import ``Config`` or any
    other code2test module so the provider remains a leaf.
    """

    def __init__(
        self,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        if not model_name:
            raise ValueError(
                "PydanticAIProvider requires model_name; got empty string."
            )
        if not api_key:
            # We deliberately construct the client here so a missing key
            # surfaces as an immediate ImportError-equivalent failure
            # instead of waiting for the first predict() call.
            raise ValueError(
                "PydanticAIProvider requires api_key. Set "
                "OPENAI_API_KEY in the environment or pass api_key=... "
                "to Config(provider='openai', ...)."
            )

        # Import lazily so the test suite can substitute a stub openai
        # module without the real one being importable.
        from openai import OpenAI

        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,
        )

    # --- request framing ---------------------------------------------------

    @staticmethod
    def _schema_json_instruction(schema: type[T]) -> str:
        """System-side instruction forcing JSON output that matches the
        schema. We rely on the model's instruction-following rather
        than tool/function-calling because (a) every OpenAI-compatible
        provider supports the former, and (b) the latter varies in
        shape across vendors.
        """
        return (
            "You are a code-analysis assistant. Respond ONLY with a "
            "single JSON object — no prose, no markdown fences, no "
            "explanations. The JSON object must conform to this schema:\n"
            f"```\n{json.dumps(schema.model_json_schema(), indent=2)}\n```"
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Pull the first balanced {...} JSON object out of a model reply.

        Models sometimes wrap JSON in prose or markdown fences despite
        strict instructions. We try to parse the whole string first;
        on failure, locate the first '{' and the matching '}' and
        parse that slice.
        """
        text = text.strip()
        # Strip a single level of markdown fence if present.
        if text.startswith("```"):
            # Strip the opening fence line; tolerate language tags.
            nl = text.find("\n")
            if nl >= 0:
                text = text[nl + 1:].rstrip()
        # Drop a trailing fence if present.
        if text.endswith("```"):
            text = text[:-3].rstrip()

        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Fall back: substring from first '{' to last '}'.
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise ValueError(
                f"Provider response does not contain JSON object: "
                f"{text[:200]!r}..."
            )
        return text[first:last + 1]

    # --- predict -----------------------------------------------------------

    def predict(self, system: str, user: str, schema: type[T]) -> T:
        """Send a chat completion; parse JSON into the schema instance.

        Raises:
            openai.OpenAIError subclasses on network or auth failure.
            ValueError when the model reply is not valid JSON for the
            schema.
        """
        # The seam accepts both system+user. We prepend the schema
        # instruction to the system prompt so the schema constraint
        # is the strongest context.
        composed_system = self._schema_json_instruction(schema) + "\n\n" + system
        composed_user = user

        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": composed_system},
                {"role": "user", "content": composed_user},
            ],
            temperature=0.0,
        )

        if not response.choices:
            raise ValueError(
                "Provider returned empty choices list; nothing to parse."
            )
        content = response.choices[0].message.content or ""
        payload = self._extract_json(content)
        return schema.model_validate_json(payload)


__all__ = ["PydanticAIProvider"]
