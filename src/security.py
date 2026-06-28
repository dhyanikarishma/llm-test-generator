"""Security helpers: input sanitization and rate limiting.

These are pure functions (no Streamlit, no clock side-effects baked in) so they
are easy to unit-test. The UI layer supplies the current time and the session's
request history.
"""

from __future__ import annotations

import re

from . import config

# Strip ASCII control characters except tab (\x09) and newline (\x0a). These can
# be used to smuggle hidden instructions or corrupt the prompt.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_spec(text: str, max_chars: int = config.MAX_SPEC_CHARS) -> str:
    """Clean and bound a user-supplied specification before it reaches the LLM.

    - Removes control characters (defence against prompt smuggling).
    - Trims surrounding whitespace.
    - Truncates to ``max_chars`` (cost + abuse guardrail).

    Note: this does NOT make prompt injection impossible (no input filter can).
    The real mitigation is that user text is wrapped in delimiters and the
    system prompt instructs the model to treat it strictly as data.
    """
    if not text:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub("", text).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    return cleaned


def check_rate_limit(
    timestamps: list[float],
    now: float,
    max_calls: int = config.RATE_LIMIT_MAX_GENERATIONS,
    window_seconds: int = config.RATE_LIMIT_WINDOW_SECONDS,
) -> tuple[bool, int, list[float]]:
    """Sliding-window rate limit.

    Args:
        timestamps: epoch seconds of prior requests in this session.
        now: current epoch seconds.
        max_calls: allowed calls per window.
        window_seconds: window length.

    Returns:
        (allowed, retry_after_seconds, pruned_timestamps)
        ``pruned_timestamps`` is the history with stale entries removed; the
        caller should store it back (and append ``now`` when allowed).
    """
    recent = [t for t in timestamps if now - t < window_seconds]
    if len(recent) >= max_calls:
        retry_after = int(window_seconds - (now - min(recent))) + 1
        return False, max(retry_after, 1), recent
    return True, 0, recent
