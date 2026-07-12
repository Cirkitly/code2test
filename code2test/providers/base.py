"""Provider base classes — synchronous and asynchronous.

A Provider returns a schema-typed object derived from a system+user
prompt. Schemas are pydantic BaseModels; the provider MUST return a
constructed (model_validate'd) instance so callers can read fields
without further parsing.

This abstraction does NOT specify retry policy, rate limiting, or
fallback chains. Those are each provider's responsibility; the seam is
intentionally narrow.
"""

from __future__ import annotations

from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Provider:
    """Synchronous provider contract.

    Subclasses must implement predict(); apredict() is optional but
    recommended so callers can use either concurrency model.
    """

    def predict(self, system: str, user: str, schema: type[T]) -> T:
        """Run the provider synchronously and return a schema instance."""
        raise NotImplementedError(
            f"{type(self).__name__} does not implement predict(); "
            "use the async interface via apredict() if appropriate."
        )

    def apredict(self, system: str, user: str, schema: type[T]) -> T:
        """Async convenience that defaults to the sync implementation.

        Subclasses with a true async backend (e.g. pydantic_ai.Agent.run)
        override this directly.
        """
        return self.predict(system, user, schema)


class AsyncProvider:
    """Asynchronous-only provider contract.

    Used when a provider has no meaningful sync implementation, e.g.
    providers that ARE just thin wrappers around async-only libraries.
    The async interface is the canonical one.
    """

    def apredict(self, system: str, user: str, schema: type[T]) -> T:  # type: ignore[override]
        raise NotImplementedError(
            f"{type(self).__name__} does not implement apredict()"
        )


__all__ = ["Provider", "AsyncProvider", "T"]
