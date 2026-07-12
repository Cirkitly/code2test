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
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Config(BaseModel):
    """Single source of runtime truth for code2test test generation.

    All fields have defaults so `Config()` is a valid zero-argument call.
    Strict typing throughout; pydantic enforces the schema at construction.
    """

    # LLM provider selection (M1A.2 uses this).
    provider: str = "stub"
    model: str = "stub-deterministic"
    base_url: str = "https://api.openai.com/v1"
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


__all__ = ["Config"]
