# Security

This project takes security seriously even though it is a portfolio app,
because it (a) handles **API keys** and (b) can **execute AI-generated code**.
This document explains the threat model, what is implemented, and why some
common web-app controls do not apply to a Python/Streamlit/LLM app.

## Threat model

| Asset | Threat | Mitigation |
|---|---|---|
| LLM API keys | Leakage / theft | Read server-side only; never sent to browser; kept out of git via `.gitignore`; set via env / platform secrets |
| LLM spend | Cost / abuse attacks | `max_tokens` cap, input length cap, per-session sliding-window rate limit |
| The server host | Remote code execution | Sandbox execution of generated code is **disabled by default** and env-gated |
| The model | Prompt injection | Input sanitized + wrapped in delimiters; system prompts contain anti-injection instructions |
| The browser | XSS | LLM output rendered as escaped Markdown / `st.code`; raw HTML is used only for the app's own static CSS |
| Dependencies | Vulnerable packages | Versions pinned; `pip-audit` runs in CI |

## What is implemented

1. **Secret hygiene** — keys live in `.env` (gitignored) or platform secrets;
   `.env.example` documents required names with empty values; keys are never
   returned to the client. See `src/config.get_api_key`.
2. **Input validation** — `src/security.sanitize_spec` strips control
   characters and truncates to `MAX_SPEC_CHARS`. Enforced inside
   `generator.generate`, so every entry point is protected.
3. **Rate limiting** — `src/security.check_rate_limit` is a sliding-window
   limiter applied per Streamlit session (`RATE_LIMIT_MAX_GENERATIONS` per
   `RATE_LIMIT_WINDOW_SECONDS`).
4. **Cost guardrails** — every LLM call sets `max_tokens`
   (`DEFAULT_MAX_TOKENS`).
5. **Prompt-injection defence** — user text is wrapped in delimiters and every
   system prompt instructs the model to treat the spec strictly as data.
6. **Safe rendering** — generated analysis/tests are shown with `st.markdown`
   (HTML escaped) and `st.code`; `unsafe_allow_html=True` is used only for the
   app's own static CSS, never for model output.
7. **Sandbox gating** — `validation.run_pytest` executes generated code and is
   only reachable when `ENABLE_SANDBOX_RUN=1`. It is OFF in any public deploy.
8. **Generic error messages** — internal exceptions are not shown to users.
9. **Dependency audit** — CI runs `pip-audit` on every push.
10. **Transport security** — when deployed on Streamlit Community Cloud, HTTPS
    is enforced by the platform; `enableXsrfProtection` and `enableCORS` are on.

## Why some checklist items do not apply here

- **SQL injection / ORM** — the app has no database.
- **bcrypt / JWT / auth** — there are no user accounts or login.
- **File-upload validation** — the app accepts text only, no uploads.
- **Wildcard CORS** — there is no separate API consumed cross-origin; Streamlit
  serves the UI and its own backend.
- **`dangerouslySetInnerHTML`** — this is a Python app, not React.

## Pre-deploy checklist

- [ ] `.env` is NOT committed (`git status` shows it ignored)
- [ ] Secrets set in the hosting platform's secret manager
- [ ] `ENABLE_SANDBOX_RUN` is unset / `0` in production
- [ ] `pip-audit` shows no unfixed high/critical issues
- [ ] HTTPS enforced (automatic on Streamlit Cloud)
- [ ] Rate limiting active (it is, by default)

## Reporting

Found an issue? Open a GitHub issue (omit sensitive details) or contact the
maintainer directly.
