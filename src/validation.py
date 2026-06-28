"""Validate (and optionally run) generated test code.

Two levels of checking:
  * ``validate_python_syntax`` — fast, safe, no execution. Uses Python's AST to
    confirm the code parses and to count test functions / assertions.
  * ``run_pytest`` — actually executes the generated PyTest suite in a
    subprocess with a timeout. This executes MODEL-GENERATED code, which is a
    remote-code-execution risk, so the UI keeps it behind an env-gated flag
    (see ``config.sandbox_run_enabled``).
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SyntaxReport:
    ok: bool
    error: str = ""
    num_tests: int = 0
    num_asserts: int = 0
    warnings: list[str] = field(default_factory=list)


def validate_python_syntax(code: str) -> SyntaxReport:
    """Parse Python code with the AST and gather quick quality metrics."""
    if not code or not code.strip():
        return SyntaxReport(ok=False, error="No code to validate.")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SyntaxReport(ok=False, error=f"Line {exc.lineno}: {exc.msg}")

    num_tests = 0
    num_asserts = 0
    uses_pytest = False
    imports_pytest = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            num_tests += 1
        if isinstance(node, ast.Assert):
            num_asserts += 1
        if isinstance(node, ast.Import):
            imports_pytest = imports_pytest or any(a.name == "pytest" for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module == "pytest":
            imports_pytest = True
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "pytest":
                uses_pytest = True

    report = SyntaxReport(ok=True, num_tests=num_tests, num_asserts=num_asserts)
    if uses_pytest and not imports_pytest:
        report.warnings.append("Uses `pytest` but is missing `import pytest`.")
    if num_tests == 0:
        report.warnings.append("No `test_*` functions were detected.")
    return report


@dataclass
class RunReport:
    ran: bool
    returncode: int = -1
    output: str = ""
    error: str = ""


def run_pytest(code: str, timeout: int = 60) -> RunReport:
    """Execute generated PyTest code in an isolated temp dir.

    SECURITY: this runs model-generated code. Only call it when execution has
    been explicitly enabled by the operator (see config.sandbox_run_enabled).
    """
    if not code or not code.strip():
        return RunReport(ran=False, error="No code to run.")

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "test_generated.py"
        test_file.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(test_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return RunReport(ran=False, error=f"Execution timed out after {timeout}s.")
        except Exception as exc:  # noqa: BLE001
            return RunReport(ran=False, error=str(exc))

        return RunReport(
            ran=True,
            returncode=proc.returncode,
            output=(proc.stdout or "") + (proc.stderr or ""),
        )
