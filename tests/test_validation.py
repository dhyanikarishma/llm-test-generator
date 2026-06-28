"""Tests for the validation module."""

from __future__ import annotations

from src.validation import run_pytest, validate_python_syntax


def test_valid_syntax_counts_tests_and_asserts():
    code = (
        "import pytest\n"
        "def test_a():\n    assert True\n"
        "def test_b():\n    assert 1 == 1\n"
    )
    report = validate_python_syntax(code)
    assert report.ok is True
    assert report.num_tests == 2
    assert report.num_asserts == 2
    assert report.warnings == []


def test_syntax_error_is_reported():
    report = validate_python_syntax("def test_bad(:\n    pass")
    assert report.ok is False
    assert "Line" in report.error


def test_warns_when_pytest_used_without_import():
    code = "@pytest.mark.parametrize('x', [1])\ndef test_x(x):\n    assert x"
    report = validate_python_syntax(code)
    assert report.ok is True
    assert any("import pytest" in w for w in report.warnings)


def test_empty_code_is_invalid():
    assert validate_python_syntax("   ").ok is False


def test_run_pytest_passes_for_trivial_suite():
    code = "def test_pass():\n    assert 1 + 1 == 2\n"
    report = run_pytest(code, timeout=60)
    assert report.ran is True
    assert report.returncode == 0


def test_run_pytest_reports_failure():
    code = "def test_fail():\n    assert 1 == 2\n"
    report = run_pytest(code, timeout=60)
    assert report.ran is True
    assert report.returncode != 0
