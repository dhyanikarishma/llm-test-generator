"""Tests for prompt construction."""

from __future__ import annotations

from src.prompts import build_analysis_prompt, build_test_prompt
from src.models import GenerationOptions


def test_test_prompt_contains_spec_and_framework_guidance():
    spec = "Passwords must contain at least 8 characters."
    prompt = build_test_prompt(spec, "pytest", GenerationOptions())
    assert spec in prompt
    assert "PyTest" in prompt


def test_test_prompt_omits_negative_when_disabled():
    options = GenerationOptions(include_negative_tests=False, include_edge_cases=False)
    prompt = build_test_prompt("spec", "pytest", options)
    assert "Negative tests" not in prompt


def test_test_prompt_includes_categories_when_enabled():
    options = GenerationOptions(include_negative_tests=True, include_edge_cases=True)
    prompt = build_test_prompt("spec", "gtest", options)
    assert "Negative tests" in prompt
    assert "Edge cases" in prompt
    assert "Google Test" in prompt


def test_analysis_prompt_lists_requested_sections():
    options = GenerationOptions(include_coverage=True)
    prompt = build_analysis_prompt("spec", options)
    assert "Coverage Suggestions" in prompt
    assert "Requirements Breakdown" in prompt
