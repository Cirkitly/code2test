"""Tests for code2test.config.Config (M1A.1).

Verifies:
  * Round-trip preserves every field (the contract).
  * Default-construction is zero-argument and produces expected defaults.
  * Invalid confidence values are rejected (the schema is enforced).
  * Provider-string leniency — Config accepts unknown providers and the
    provider seam raises with a clearer message.
  * file I/O is atomic-ish; parent dirs are created.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from code2test.config import Config


def test_config_zero_arg_construction():
    """Config() with no args uses the project's deployment-target defaults.

    v1.1: defaults are no longer 'stub' / 'stub-deterministic' — they are
    the MiniMax-compatible deployment target. Operators who want the
    offline default must construct Config(provider='stub') explicitly.
    """
    cfg = Config()
    # Defaults reflect the project's deployment target (v1.1); operators
    # override via OPENAI_* env or constructor args.
    assert cfg.provider == "openai"
    assert cfg.base_url == "https://api.minimax.io/v1"
    # Default model is a placeholder that the operator MUST override
    # via OPENAI_MODEL or the call will fail loudly at predict() time.
    assert cfg.model == "REPLACE-ME-WITH-OPENAI_MODEL"
    assert cfg.confidence_threshold == pytest.approx(0.6)
    assert cfg.auto_accept is False
    assert cfg.dry_run is False
    assert cfg.framework == "pytest"


def test_config_round_trip_preserves_every_field(tmp_path):
    cfg = Config(
        provider="openai",
        model="gpt-4o-mini",
        base_url="https://api.example.com/v1",
        api_key="sk-test-abc",
        confidence_threshold=0.75,
        auto_accept=True,
        dry_run=False,
        output_dir="alt_tests",
        framework="pytest",
        max_tokens=4096,
        max_tests_per_component=12,
        include_edge_cases=True,
        include_fixtures=False,
    )
    path = tmp_path / "nested" / "config.json"
    cfg.to_path(path)

    assert path.exists()
    again = Config.from_path(path)

    # Field-by-field equality. Tests the round-trip is lossless, not just
    # approximately equal.
    for fld in Config.model_fields:
        assert getattr(again, fld) == getattr(cfg, fld), (
            f"Round-trip lost field {fld!r}: {getattr(again, fld)!r} vs "
            f"{getattr(cfg, fld)!r}"
        )


def test_to_path_creates_parent_directories(tmp_path):
    cfg = Config(provider="stub")
    deep = tmp_path / "a" / "b" / "c" / "config.json"
    cfg.to_path(deep)
    assert deep.exists()


def test_confidence_threshold_must_be_in_range():
    with pytest.raises(ValidationError):
        Config(confidence_threshold=1.5)
    with pytest.raises(ValidationError):
        Config(confidence_threshold=-0.1)


def test_max_tests_per_component_must_be_at_least_one():
    with pytest.raises(ValidationError):
        Config(max_tests_per_component=0)


def test_provider_string_lenient():
    """We accept an unknown provider here; the provider seam raises later."""
    cfg = Config(provider="made-up-thing")
    assert cfg.provider == "made-up-thing"


def test_round_trip_through_to_dict():
    cfg = Config(provider="openai", model="x")
    d = cfg.to_dict()
    again = Config.model_validate(d)
    assert again.provider == cfg.provider
    assert again.model == cfg.model


# --- Config.from_env tests --------------------------------------------

def test_from_env_reads_provider_from_env(monkeypatch):
    """from_env() reads CODE2TEST_PROVIDER, OPENAI_BASE_URL,
    OPENAI_MODEL, OPENAI_API_KEY from the environment.
    """
    monkeypatch.setenv("CODE2TEST_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    cfg = Config.from_env()
    assert cfg.provider == "openai"
    assert cfg.base_url == "https://example.test/v1"
    assert cfg.model == "test-model"
    assert cfg.api_key == "sk-test"


def test_from_env_uses_module_defaults_when_unset(monkeypatch):
    """When env vars are missing, defaults match the project deployment
    target (provider=openai, base_url=...minimax.../v1).
    """
    for v in ("CODE2TEST_PROVIDER", "OPENAI_BASE_URL", "OPENAI_MODEL",
              "OPENAI_API_KEY"):
        monkeypatch.delenv(v, raising=False)

    cfg = Config.from_env()
    assert cfg.provider == "openai"
    assert cfg.base_url == "https://api.minimax.io/v1"


def test_from_env_constructor_overrides_win():
    """Constructor-style kwargs override env vars. This is the
    documented precedence: env defaults, caller overrides.
    """
    import os
    os.environ["OPENAI_BASE_URL"] = "https://env.example/v1"
    try:
        cfg = Config.from_env(base_url="https://caller.example/v1")
        assert cfg.base_url == "https://caller.example/v1"
    finally:
        del os.environ["OPENAI_BASE_URL"]


def test_from_env_constructor_only_uses_known_fields():
    """from_env() rejects unknown kwargs; silent ignore would mask typos."""
    with pytest.raises(TypeError, match="unknown field"):
        Config.from_env(provider="openai", not_a_field="x")


def test_config_to_path_and_back_round_trip_includes_new_env_layer(tmp_path):
    """File round-trip preserves the project deployment defaults."""
    cfg = Config(provider="openai", api_key="sk-x", model="m")
    path = tmp_path / "c.json"
    cfg.to_path(path)
    again = Config.from_path(path)
    assert again.provider == "openai"
    assert again.base_url == "https://api.minimax.io/v1"
