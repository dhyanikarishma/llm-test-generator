"""Tests for data models."""

from __future__ import annotations

from src.models import FrameworkResult, GenerationOptions, GenerationResult


def test_default_options():
    options = GenerationOptions()
    assert options.frameworks == ["pytest"]
    assert options.include_edge_cases is True
    assert options.include_negative_tests is True
    assert options.include_coverage is True


def test_result_succeeded_true_with_valid_code():
    result = GenerationResult(spec="x")
    result.framework_results.append(
        FrameworkResult("pytest", "PyTest", "python", "test.py", code="assert True")
    )
    assert result.succeeded is True


def test_result_succeeded_false_when_only_errors():
    result = GenerationResult(spec="x")
    result.framework_results.append(
        FrameworkResult("pytest", "PyTest", "python", "test.py", code="", error="nope")
    )
    assert result.succeeded is False
