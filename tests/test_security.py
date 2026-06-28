"""Tests for the security helpers."""

from __future__ import annotations

from src import config
from src.security import check_rate_limit, sanitize_spec


def test_sanitize_strips_control_characters():
    dirty = "valid\x00text\x07here\x1f"
    assert sanitize_spec(dirty) == "validtexthere"


def test_sanitize_keeps_newlines_and_tabs():
    text = "line1\n\tline2"
    assert sanitize_spec(text) == "line1\n\tline2"


def test_sanitize_truncates_to_max_chars():
    out = sanitize_spec("a" * 100, max_chars=10)
    assert len(out) == 10


def test_sanitize_handles_empty():
    assert sanitize_spec("") == ""
    assert sanitize_spec("   ") == ""


def test_rate_limit_allows_within_budget():
    allowed, retry, pruned = check_rate_limit([], now=1000.0, max_calls=3, window_seconds=60)
    assert allowed is True
    assert retry == 0


def test_rate_limit_blocks_when_exceeded():
    times = [1000.0, 1001.0, 1002.0]
    allowed, retry, pruned = check_rate_limit(times, now=1003.0, max_calls=3, window_seconds=60)
    assert allowed is False
    assert retry > 0


def test_rate_limit_prunes_old_entries():
    # Two old (outside window) + one recent => allowed again.
    times = [10.0, 20.0, 999.0]
    allowed, retry, pruned = check_rate_limit(times, now=1000.0, max_calls=3, window_seconds=60)
    assert allowed is True
    assert pruned == [999.0]


def test_sandbox_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_SANDBOX_RUN", raising=False)
    assert config.sandbox_run_enabled() is False


def test_sandbox_can_be_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_SANDBOX_RUN", "1")
    assert config.sandbox_run_enabled() is True
