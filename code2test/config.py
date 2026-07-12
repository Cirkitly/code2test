"""Canonical Config schema for code2test.

This is the v1.0 single source of truth for runtime configuration. Older
modules (code2test.cli.config_manager, code2test.cli.models.config,
code2test.src.config) wrap or alias this — none of them owns fields.

Architecture decision (M1A.1):
    The canonical Config lives here at the package root, alongside
    code2test.__init__. It is intentionally NOT named code2test.cli.* to
    keep it out of the CLI sub-command discovery path (CLI loads lazily).

Wire-up:
    - code2test/cli/config_manager.ConfigManager -> serializes to Config.to_path
    - code2test/cli/models/config.AgentInstructions -> excluded; only test
      generation cares about Config, not the legacy docs command.
    - code2test/src/config.Config -> legacy CodeWiki docs config, untouched
      and out of v1.0 scope.

Round-trip invariant: any Config.to_path(...) -> Config.from_path(...) pair
preserves every field. Verified in tests/unit/test_config.py.

Environment-variable contract (v1.1):
    ``Config.from_env()`` reads defaults from the operator's environment
    under the names below. Constructor arguments always win over the
    environment. Defaults are the project's deployment target
    (MiniMax-compatible OpenAI endpoint); operator overrides are
    honored without code changes.

        CODE2TEST_PROVIDER  -> provider           default: "openai"
        OPENAI_BASE_URL     -> base_url          default: https://api.minimax.io/v1
        OPENAI_MODEL        -> model             default: see Config.field
        OPENAI_API_KEY      -> api_key           default: "" (no real call without key)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# Project-default deployment target. Operator overrides via env or
# constructor. Constants live here so they appear exactly once.
_DEFAULT_BASE_URL = "https://api.minimax.io/v1"
_DEFAULT_PROVIDER = "openai"
# Default model is intentionally a must-override placeholder. The
# project's deployment target name is read from $OPENAI_MODEL at
# runtime; we don't pick one here because the goal of v1.1 task 3a
# is to verify the *seam*, not to commit to a specific model name.
_DEFAULT_MODEL = "REPLACE-ME-WITH-OPENAI_MODEL"


class Config(BaseModel):
    """Single source of runtime truth for code2test test generation.

    All fields have defaults so ``Config()`` is a valid zero-argument call.
    For real LLM runs, use ``Config.from_env()`` which reads the OpenAI-
    compatible defaults from the environment.

    Stricter providers (e.g. ``provider="openai"``) require ``api_key`` to
    be set; this is enforced by the provider seam at construction time,
    not by Config itself, so a no-arg ``Config()`` remains valid as a
    *config-only* object (useful for unit tests that never trigger a
    real call).
    """

    # LLM provider selection and connection. v1.1 defaults are the
    # project's deployment target (OpenAI-compatible endpoint).
    provider: str = _DEFAULT_PROVIDER
    model: str = _DEFAULT_MODEL
    base_url: str = _DEFAULT_BASE_URL
    api_key: str = ""

    # Generation behavior.
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    auto_accept: bool = False
    dry_run: bool = False
    max_tests_per_component: int = Field(default=10, ge=1, le=100)
    include_edge_cases: bool = True
    include_fixtures: bool = True

    # Output.
    output_dir: str = "tests"
    framework: str = "pytest"   # pytest | unittest | jest | junit
    max_tokens: int = Field(default=2048, ge=64, le=32000)

    @model_validator(mode="after")
    def _validate_provider(self) -> "Config":
        """Stub provider must not require a base_url or api_key, but we
        tolerate empty strings; real providers will surface this as an
        error at provider construction time (M1A.2).
        """
        known_providers = {"stub", "openai", "pydantic-ai"}
        if self.provider not in known_providers:
            # We don't raise — the provider seam raises with a clearer
            # message at first predict() call. Letting Config be permissive
            # keeps the round-trip test honest.
            pass
        return self

    # --- (de)serialization ------------------------------------------------

    def to_path(self, path: Path) -> None:
        """Serialize to JSON on disk. Atomic-ish: writes, no fsync."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def from_path(cls, path: Path) -> "Config":
        """Hydrate from JSON on disk."""
        path = Path(path)
        return cls.model_validate_json(path.read_text())

    def to_dict(self) -> dict:
        """For JSON reporting; preserves every field."""
        return self.model_dump()

    # --- environment variables --------------------------------------------

    @classmethod
    def from_env(cls, **overrides) -> "Config":
        """Build a Config from operator environment variables.

        Reads (per the env contract documented in this module's
        docstring):

            CODE2TEST_PROVIDER  -> provider
            OPENAI_BASE_URL     -> base_url
            OPENAI_MODEL        -> model
            OPENAI_API_KEY      -> api_key

        All four are optional. If unset, the field falls back to the
        Config field default.

        Constructor-style keyword arguments passed via ``overrides``
        take precedence over the environment. This means:

            Config.from_env()                       # env-or-default
            Config.from_env(provider="stub")         # overrides env
            Config.from_env(api_key="...")          # overrides env
            Config(provider="stub")                 # bypasses env

        ``overrides`` values are only honored for keys that exist in
        Config.model_fields, so typo'd keys raise TypeError.
        """
        env_overrides = {
            "provider": os.environ.get("CODE2TEST_PROVIDER", _DEFAULT_PROVIDER),
            "base_url": os.environ.get("OPENAI_BASE_URL", _DEFAULT_BASE_URL),
            "model": os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL),
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
        }
        # Caller arguments win over the environment.
        for k in overrides:
            if k not in cls.model_fields:
                raise TypeError(
                    f"Config.from_env(): unknown field {k!r}; valid "
                    f"fields: {sorted(cls.model_fields)}"
                )
        merged = {**env_overrides, **overrides}
        return cls(**merged)


__all__ = ["Config"]  # noqa: F401
