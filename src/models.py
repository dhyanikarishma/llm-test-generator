"""Data models used across the app.

Using small dataclasses (instead of loose dictionaries) makes the code
self-documenting and much easier to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GenerationOptions:
    """User-selected options that shape what the AI produces."""

    frameworks: list[str] = field(default_factory=lambda: ["pytest"])
    include_edge_cases: bool = True
    include_negative_tests: bool = True
    include_coverage: bool = True
    self_critique: bool = False
    traceability: bool = False


@dataclass
class FrameworkResult:
    """The generated test code for a single framework."""

    framework: str
    label: str
    language: str
    filename: str
    code: str
    critique: str = ""
    error: str | None = None


@dataclass
class GenerationResult:
    """Everything produced from a single 'Generate' click."""

    spec: str
    analysis: str = ""
    traceability: str = ""
    framework_results: list[FrameworkResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return any(r.code and not r.error for r in self.framework_results)
