"""Tests for the core generation pipeline."""

from __future__ import annotations

from src.generator import generate, split_critique, strip_code_fences
from src.models import GenerationOptions
from tests.conftest import FakeLLMClient


def test_strip_code_fences_extracts_block():
    text = "Here you go:\n```python\nx = 1\n```\nDone."
    assert strip_code_fences(text) == "x = 1"


def test_strip_code_fences_without_fence_returns_trimmed():
    assert strip_code_fences("import os") == "import os"


def test_strip_code_fences_drops_leading_prose_without_fence():
    reply = "Here are the tests:\n\nimport pytest\n\ndef test_x():\n    assert True"
    out = strip_code_fences(reply)
    assert out.startswith("import pytest")
    assert "Here are the tests" not in out


def test_strip_code_fences_handles_empty():
    assert strip_code_fences("") == ""


def test_generate_empty_spec_returns_error(fake_client):
    result = generate("   ", GenerationOptions(), fake_client)
    assert not result.succeeded
    assert result.errors
    assert fake_client.calls == []


def test_generate_produces_code_for_each_framework(fake_client):
    options = GenerationOptions(frameworks=["pytest", "gtest", "robot"])
    result = generate("Passwords must be 8+ characters.", options, fake_client)
    assert result.succeeded
    assert len(result.framework_results) == 3
    assert {r.framework for r in result.framework_results} == {"pytest", "gtest", "robot"}
    for r in result.framework_results:
        assert r.code
        assert r.error is None


def test_generate_includes_analysis_when_requested(fake_client):
    options = GenerationOptions(frameworks=["pytest"], include_coverage=True)
    result = generate("Accounts lock after 5 failed attempts.", options, fake_client)
    assert result.analysis != ""


def test_generate_skips_analysis_when_all_categories_off(fake_client):
    options = GenerationOptions(
        frameworks=["pytest"],
        include_edge_cases=False,
        include_negative_tests=False,
        include_coverage=False,
    )
    result = generate("Some spec.", options, fake_client)
    assert result.analysis == ""


def test_generate_unknown_framework_records_error(fake_client):
    options = GenerationOptions(frameworks=["does_not_exist"])
    result = generate("Some spec.", options, fake_client)
    assert any("Unknown framework" in e for e in result.errors)


def test_generate_handles_model_failure_per_framework(failing_client):
    options = GenerationOptions(frameworks=["pytest"])
    result = generate("Some spec.", options, failing_client)
    assert not result.succeeded
    assert result.framework_results[0].error is not None


def test_split_critique_separates_notes_and_code():
    reply = "## Review\n- weak assertion\n\n## Improved Tests\n```python\nassert True\n```"
    notes, improved = split_critique(reply)
    assert "weak assertion" in notes
    assert improved == "assert True"


def test_generate_self_critique_replaces_code_and_keeps_notes():
    reply = "## Review\n- add edge case\n\n```python\ndef test_better():\n    assert True\n```"
    client = FakeLLMClient(response=reply)
    options = GenerationOptions(frameworks=["pytest"], self_critique=True)
    result = generate("Passwords must be 8+ chars.", options, client)
    fw = result.framework_results[0]
    assert "def test_better" in fw.code
    assert "add edge case" in fw.critique


def test_generate_traceability_matrix(fake_client):
    options = GenerationOptions(frameworks=["pytest"], traceability=True)
    result = generate("Accounts lock after 5 attempts.", options, fake_client)
    assert result.traceability != ""


def test_generate_sanitizes_oversized_spec(fake_client):
    from src import config

    huge = "a" * (config.MAX_SPEC_CHARS + 500)
    result = generate(huge, GenerationOptions(frameworks=["pytest"]), fake_client)
    assert len(result.spec) <= config.MAX_SPEC_CHARS
