<div align="center">

# 🧪 LLM Test-Case Generator for Software Specifications

**Turn plain-English requirements into runnable test suites — PyTest, Google Test (C++), and Robot Framework — complete with edge cases, negative tests, coverage suggestions, a traceability matrix, and a self-critique pass.**

---

## 📌 Problem Statement

Writing tests is one of the most time-consuming and skipped parts of software
engineering. Edge cases and negative paths are routinely missed — exactly the
gaps that cause production incidents in high-reliability systems like telecom
infrastructure.

**This tool closes that gap.** Paste a specification, and an LLM acts as a
senior QA engineer: it analyses the requirements, designs a test strategy, and
generates ready-to-run test code across multiple frameworks and languages.

> Built by an engineer with hands-on **telecom software-validation** experience,
> where rigorous, exhaustive testing isn't optional — it's the standard.

---

## ✨ Features

- **Multi-framework output** — PyTest (Python), Google Test (C++), Robot Framework.
- **Multi-provider** — Groq and Google Gemini, switchable in the UI.
- **Edge & boundary cases** — boundary-value analysis baked into the prompts.
- **Negative testing** — invalid input and failure-path coverage.
- **Coverage suggestions** — what to measure and which requirements are ambiguous.
- **Requirement → test traceability matrix** — see which tests cover which requirement.
- **Self-critique pass** — the model reviews and rewrites its own tests.
- **Live validation** — AST syntax check + optional (gated) sandboxed PyTest run.
- **Download everything** — one-click `.zip` of all tests, analysis, and matrix.
- **Secure by design** — see [Security](#-security).
- **CI/CD** — GitHub Actions runs tests on Python 3.10–3.12 and audits dependencies.

---


## 🏗️ Architecture

The app is split into a UI layer and a pure, testable core engine. The LLM is
accessed through a minimal `complete()` interface, so the engine can be tested
with a fake client and new providers can be added without touching the engine.

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI; wires in rate limiting, input caps, safe rendering |
| `src/generator.py` | Core pipeline: sanitize → prompt → LLM → parse |
| `src/prompts.py` | Prompt engineering (+ anti-prompt-injection clauses) |
| `src/llm_client.py` | Groq / Gemini clients behind one `LLMClient` interface |
| `src/security.py` | Input sanitization + sliding-window rate limiting |
| `src/validation.py` | AST syntax checks + (gated) sandboxed PyTest execution |
| `src/models.py` | Typed data structures |
| `src/config.py` | Settings, providers, frameworks, security guardrails |
| `.github/workflows/tests.yml` | CI: tests on 3.10–3.12 + `pip-audit` |
| `tests/` | Unit tests using a fake LLM client (no network needed) |

---

## 🔒 Security

Because this app handles API keys and can execute AI-generated code, it ships
with real safeguards (full details in [SECURITY.md](SECURITY.md)):

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md). Highlights: more providers, file/PDF upload,
stub-implementation generation, and coverage estimation.

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and learn from.
