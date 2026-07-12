"""Provider seam for code2test.

The contract:
    provider.predict(system, user, schema) -> schema_instance
    provider.apredict(system, user, schema) -> schema_instance   (async)

This is the ONE seam agents talk to. v1.1 ships two implementations:

    StubProvider              — deterministic, offline, used by tests/CI
    PydanticAIProvider        — generic OpenAI-SDK client. Backend-
                                agnostic: defaults the project's
                                deployment target to a MiniMax-compatible
                                endpoint, but any base_url/api_key
                                combination works with the same code path.
                                No vendor-specific branches; the only
                                configurable knobs are base_url, api_key,
                                model_name.

Adding a new provider means adding a subclass and updating
``get_provider``'s dispatch. Nothing in code2test.agents/* needs to
change.

Architectural rule: the LLM-typed providers in code2test/src/be/* are
DOCS subsystem (legacy CodeWiki) and remain independent of this seam.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import AsyncProvider, Provider, T
from .stub import StubProvider

if TYPE_CHECKING:
    # Imported lazily because importing the openai SDK at module load
    # time triggers network-environment introspection that we want to
    # remain opt-in.
    from .pydantic_ai_provider import PydanticAIProvider
    from code2test.config import Config


def get_provider(config: "Config") -> Provider:
    """Construct the right Provider implementation based on Config.provider.

    Provider selection:
        "stub"          -> StubProvider (deterministic, offline)
        "openai"        -> PydanticAIProvider (OpenAI-SDK-backed)
        "pydantic-ai"   -> PydanticAIProvider (alias kept for v1.0
                            compatibility; same code path)
        anything else   -> ValueError with a clear message

    The 'openai' / 'pydantic-ai' instance carries model_name,
    base_url, and api_key from Config. PydanticAIProvider enforces
    api_key at construction; we forward whatever Config has.
    """
    if config.provider == "stub":
        return StubProvider()

    # Lazy import: only pay for the openai SDK when explicitly requested.
    from .pydantic_ai_provider import PydanticAIProvider

    if config.provider in ("openai", "pydantic-ai"):
        return PydanticAIProvider(
            model_name=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
        )

    raise ValueError(
        f"Unknown provider: {config.provider!r}. "
        f"Supported: 'stub' (offline), 'openai' (OpenAI-SDK-backed)."
    )


__all__ = [
    "Provider",
    "AsyncProvider",
    "StubProvider",
    "get_provider",
    "T",
]  # noqa: F401
