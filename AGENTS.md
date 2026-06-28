# Project rules for AI coding assistants

These rules apply to ALL code generated in this repository.

## Security (non-negotiable)

1. Secrets
   - API keys, tokens, and URLs live ONLY in `.env` (gitignored) or platform secrets.
   - Never hardcode a secret in source. Read keys server-side via `os.environ`.
   - Never return a secret to the client or print it to logs.

2. Input validation
   - Treat ALL user input as untrusted. Sanitize and length-bound it on the
     server (see `src/security.sanitize_spec`) before use.

3. LLM safety
   - Always set `max_tokens` on LLM calls (cost guardrail).
   - Wrap user content in delimiters and keep the anti-injection clause in
     every system prompt.
   - Rate-limit generation per session (see `src/security.check_rate_limit`).
   - Never execute model-generated code unless `ENABLE_SANDBOX_RUN=1`.

4. Output rendering
   - Render LLM output only via escaped Markdown (`st.markdown` default) or
     `st.code`. Do NOT pass model output to `unsafe_allow_html=True`.

5. Error handling
   - Show users generic messages. Never leak stack traces or internal details.

6. Dependencies
   - Pin versions in `requirements.txt`. Keep `pip-audit` clean.

## Engineering conventions

- Keep LLM/network code behind the `LLMClient` interface so the core engine
  stays unit-testable with a fake client (no network in tests).
- Add or update unit tests for any new behaviour; `pytest` must stay green.
- Prefer small, typed dataclasses over loose dicts for data passed around.
