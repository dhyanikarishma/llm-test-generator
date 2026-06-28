"""Central configuration for the LLM Test-Case Generator.

Keeping all settings in one place makes the app easy to tweak and to test.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# LLM tuning
# ---------------------------------------------------------------------------
# Low temperature => more deterministic, focused test code.
DEFAULT_TEMPERATURE = 0.2

# Hard cap on tokens per response. This is also a COST-CONTROL guardrail:
# it bounds how much a single request can spend, limiting cost-attack damage.
DEFAULT_MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# Security guardrails
# ---------------------------------------------------------------------------
# Reject specifications longer than this. Prevents oversized prompts that waste
# tokens/money and could be used for abuse.
MAX_SPEC_CHARS = 8000

# Per-session rate limit: at most MAX_GENERATIONS requests per WINDOW seconds.
# Mitigates cost attacks and accidental hammering of the LLM API.
RATE_LIMIT_MAX_GENERATIONS = 8
RATE_LIMIT_WINDOW_SECONDS = 60


def sandbox_run_enabled() -> bool:
    """Whether the 'run generated tests in a sandbox' feature is allowed.

    Executing model-generated code is a remote-code-execution risk on a public
    deployment, so it is DISABLED by default and must be explicitly turned on
    (e.g. for local development) via ``ENABLE_SANDBOX_RUN=1``.
    """
    return os.environ.get("ENABLE_SANDBOX_RUN", "0").strip().lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, dict] = {
    "groq": {
        "label": "Groq (free)",
        "env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
        ],
        "key_url": "https://console.groq.com/keys",
    },
    "gemini": {
        "label": "Google Gemini (free tier)",
        "env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "models": [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-flash-latest",
        ],
        "key_url": "https://aistudio.google.com/app/apikey",
    },
}

DEFAULT_PROVIDER = "groq"
DEFAULT_MODEL = PROVIDERS[DEFAULT_PROVIDER]["default_model"]


# ---------------------------------------------------------------------------
# Supported test frameworks
# ---------------------------------------------------------------------------
FRAMEWORKS: dict[str, dict[str, str]] = {
    "pytest": {
        "label": "PyTest (Python)",
        "language": "python",
        "extension": "py",
        "filename": "test_generated.py",
    },
    "gtest": {
        "label": "Google Test (C++)",
        "language": "cpp",
        "extension": "cpp",
        "filename": "test_generated.cpp",
    },
    "robot": {
        "label": "Robot Framework",
        "language": "robotframework",
        "extension": "robot",
        "filename": "test_generated.robot",
    },
}


def get_api_key(provider: str = DEFAULT_PROVIDER) -> str | None:
    """Find a provider's API key from the environment or Streamlit secrets.

    Keys are ONLY ever read server-side here; they are never sent to the
    browser or included in any response to the client.
    """
    meta = PROVIDERS.get(provider, PROVIDERS[DEFAULT_PROVIDER])
    env_var = meta["env"]

    key = os.environ.get(env_var)
    if key:
        return key.strip()

    try:
        import streamlit as st

        secret = st.secrets.get(env_var)  # type: ignore[attr-defined]
        if secret:
            return str(secret).strip()
    except Exception:
        pass

    return None
