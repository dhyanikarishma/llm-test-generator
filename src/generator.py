"""Core orchestration: spec in, structured test suite out.

This module is deliberately free of any UI or network code. It receives an
``LLMClient`` (real or fake), which makes the whole pipeline unit-testable.

Security: the incoming spec is sanitized and length-bounded here, so every
caller (UI today, an API tomorrow) gets the same protection.
"""

from __future__ import annotations

import re

from . import config, prompts, security
from .llm_client import LLMClient
from .models import FrameworkResult, GenerationOptions, GenerationResult

_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n(.*?)```", re.DOTALL)

_CODE_START_RE = re.compile(
    r"""^\s*(
        import\s | from\s | def\s | class\s | @ | \#
        | \"\"\" | ''' | async\s
        | TEST | TEST_F | \*\*\*
    )""",
    re.VERBOSE,
)


def strip_code_fences(text: str) -> str:
    """Return raw code from a model reply, removing Markdown and leading prose."""
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    lines = text.strip().splitlines()
    for i, line in enumerate(lines):
        if _CODE_START_RE.match(line):
            return "\n".join(lines[i:]).strip()
    return text.strip()


def split_critique(reply: str) -> tuple[str, str]:
    """Split a critique reply into (review_notes, improved_code)."""
    improved = strip_code_fences(reply)
    match = _FENCE_RE.search(reply or "")
    notes = reply[: match.start()].strip() if match else ""
    return notes, improved


def generate(
    spec: str,
    options: GenerationOptions,
    client: LLMClient,
) -> GenerationResult:
    """Generate analysis, per-framework tests, optional critique + matrix."""
    spec = security.sanitize_spec(spec, config.MAX_SPEC_CHARS)
    result = GenerationResult(spec=spec)

    if not spec:
        result.errors.append("Specification is empty. Please describe the feature to test.")
        return result

    if options.include_coverage or options.include_edge_cases or options.include_negative_tests:
        try:
            analysis = client.complete(
                prompts.ANALYSIS_SYSTEM_PROMPT,
                prompts.build_analysis_prompt(spec, options),
            )
            result.analysis = analysis.strip()
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"Analysis generation failed: {exc}")

    for fw in options.frameworks:
        meta = config.FRAMEWORKS.get(fw)
        if meta is None:
            result.errors.append(f"Unknown framework: {fw}")
            continue

        fw_result = FrameworkResult(
            framework=fw,
            label=meta["label"],
            language=meta["language"],
            filename=meta["filename"],
            code="",
        )
        try:
            raw = client.complete(
                prompts.TEST_SYSTEM_PROMPT,
                prompts.build_test_prompt(spec, fw, options),
            )
            fw_result.code = strip_code_fences(raw)
            if not fw_result.code:
                fw_result.error = "Model returned an empty response."
            elif options.self_critique:
                try:
                    critique_reply = client.complete(
                        prompts.CRITIQUE_SYSTEM_PROMPT,
                        prompts.build_critique_prompt(fw, fw_result.code),
                    )
                    notes, improved = split_critique(critique_reply)
                    if improved:
                        fw_result.code = improved
                    fw_result.critique = notes
                except Exception as exc:  # noqa: BLE001
                    fw_result.critique = f"_Critique pass failed: {exc}_"
        except Exception as exc:  # noqa: BLE001
            fw_result.error = str(exc)

        result.framework_results.append(fw_result)

    if options.traceability:
        primary = next((r for r in result.framework_results if r.code and not r.error), None)
        if primary is not None:
            try:
                matrix = client.complete(
                    prompts.TRACEABILITY_SYSTEM_PROMPT,
                    prompts.build_traceability_prompt(spec, primary.code),
                )
                result.traceability = matrix.strip()
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Traceability matrix failed: {exc}")

    return result
