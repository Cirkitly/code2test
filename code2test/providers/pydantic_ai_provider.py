"""Pydantic-AI backed provider (v1.0: scaffolding only).

In v1.0, this provider raises NotImplementedError on every predict() so
that an "openai" or "pydantic-ai" config doesn't pretend to work without
real wiring. The seam is in place — agents talk to it — but the actual
network call lands in v1.1.

v1.1 plan:
    1. Wrap pydantic_ai.Agent. The Agent's `output_type` becomes the seam
       schema passed at predict() time.
    2. Add a retry helper for 429s.
    3. Reuse code2test.config.Config.model/base_url/api_key for
       provider/credentials.
    4. Add a streaming variant for long completions (currently the
       verifier reads back result.output, not the stream).

Until then, raise NotImplementedError on apredict() and let get_provider
keep returning an instance (so Config schemas with provider="openai"
load without crashing on import).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Provider, T

if TYPE_CHECKING:
    pass


class PydanticAIProvider(Provider):
    """v1.0 placeholder. Real wiring lands in v1.1.

    Construct without crashing; raise on first use.
    """

    def __init__(self, model_name: str, base_url: str | None = None,
                 api_key: str | None = None) -> None:
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key

    def predict(self, system: str, user: str, schema: type[T]) -> T:
        raise NotImplementedError(
            "PydanticAIProvider.predict() is not implemented in v1.0. "
            "Use provider='stub' for deterministic offline runs. "
            "Real LLM calls land in v1.1."
        )


__all__ = ["PydanticAIProvider"]
