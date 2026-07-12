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
    cfg = Config()
    assert cfg.provider == "stub"
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
