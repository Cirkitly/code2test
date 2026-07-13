"""Unit tests for the runner's JSON serialization helper.

The runner writes the recorded JSON with an `_events` array so the
variance script can partition the failure space without re-running
the harness. These tests pin the serialization contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from code2testbench.runner import _serialize_events
from code2testbench.collector import EventCollector

from code2test.events import (
    IntentExtracted,
    RewriteAttempted,
    VerificationCompleted,
    RewriteCommitted,
)


def test_serialize_events_includes_type_discriminator():
    """Each serialized event has a `_type` field naming its class."""
    sink = EventCollector()
    sink.emit(IntentExtracted(run_id="r", component_id="a",
                              confidence=0.9, accepted=True))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=1, failed=0, failure_ids=(),
    ))

    out = _serialize_events(sink)
    assert [e["_type"] for e in out] == [
        "IntentExtracted", "VerificationCompleted",
    ]


def test_serialize_events_preserves_all_fields():
    sink = EventCollector()
    sink.emit(IntentExtracted(
        run_id="r1", component_id="c1",
        confidence=0.85, accepted=True,
    ))
    sink.emit(RewriteAttempted(
        run_id="r1", component_id="c1", failure_id="t1",
        success=True, strategy="test_rewrite",
        failure_classification="TEST_WRONG",
        elapsed_seconds=4.2,
    ))
    sink.emit(RewriteCommitted(
        run_id="r1", component_id="c1",
        strategy="test_rewrite", failure_classification="TEST_WRONG",
        isolated_passed=3, isolated_failed=0,
        replaced=True, success=True,
    ))
    sink.emit(VerificationCompleted(
        run_id="r1", component_id="c1",
        passed=3, failed=0, failure_ids=(), rerun=True,
    ))

    out = _serialize_events(sink)
    # Round-trip through JSON to ensure full serializability.
    blob = json.dumps(out, default=str)
    parsed = json.loads(blob)

    # RewriteCommitted should carry its boolean field faithfully.
    rc = [e for e in parsed if e["_type"] == "RewriteCommitted"][0]
    assert rc["isolated_passed"] == 3
    assert rc["isolated_failed"] == 0
    assert rc["replaced"] is True

    # VerificationCompleted rerun flag survives the round-trip.
    vc = [e for e in parsed if e["_type"] == "VerificationCompleted"][0]
    assert vc["rerun"] is True


def test_serialize_events_empty_sink():
    sink = EventCollector()
    assert _serialize_events(sink) == []
