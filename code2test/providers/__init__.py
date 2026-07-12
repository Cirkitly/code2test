"""Provider seam for code2test (M1A.2).

The contract:
    provider.predict(system, user, schema) -> schema_instance
    provider.apredict(system, user, schema) -> schema_instance   (async)

This is the ONE seam agents talk to. v1.0 ships two implementations:

    StubProvider              — deterministic, offline, used by tests/CI
    PydanticAIProvider        — wraps pydantic_ai.Agent; raises
                                NotImplementedError in v1.0 (real wiring
                                lands in v1.1)

Adding a new provider means adding a subclass and updating get_provider's
dispatch. Nothing in code2test.agents/* needs to change.

Architectural rule: the LLM-typed providers in code2test/src/be/* are
DOCS subsystem (legacy CodeWiki) and remain independent of this seam.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import AsyncProvider, Provider, T
from .stub import StubProvider

if TYPE_CHECKING:
    # Imported lazily because importing the pydantic-ai provider pulls in
    # pydantic-ai at module load time; we want that to remain opt-in.
    from .pydantic_ai_provider import PydanticAIProvider
    from code2test.config import Config


def get_provider(config: "Config") -> Provider:
    """Construct the right Provider implementation based on Config.provider.

    Provider selection:
        "stub"          -> StubProvider
        "openai"        -> PydanticAIProvider (v1.0: raises NotImplementedError)
        "pydantic-ai"   -> PydanticAIProvider (v1.0: raises NotImplementedError)
        anything else   -> ValueError with a clear message

    Returns the sync Provider interface. For async use, providers also
    expose apredict(). Most code2test agents are async, but a Provider
    is callable in both contexts.
    """
    if config.provider == "stub":
        return StubProvider()

    # Lazy import: only pay for pydantic-ai when explicitly requested.
    from .pydantic_ai_provider import PydanticAIProvider

    if config.provider in ("openai", "pydantic-ai"):
        return PydanticAIProvider(
            model_name=config.model,
            base_url=config.base_url or None,
            api_key=config.api_key or None,
        )

    raise ValueError(
        f"Unknown provider: {config.provider!r}. "
        f"Supported in v1.0: 'stub' (offline). "
        f"Real LLM providers land in v1.1."
    )


__all__ = [
    "Provider",
    "AsyncProvider",
    "StubProvider",
    "get_provider",
    "T",
]
