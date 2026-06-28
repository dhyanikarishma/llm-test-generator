# Roadmap

This document tracks where the project is headed. It doubles as a backlog for
GitHub Issues and Milestones.

## v1.1 — Current
- [x] Multi-framework output (PyTest, Google Test, Robot Framework)
- [x] Multi-provider (Groq, Gemini)
- [x] Self-critique pass and traceability matrix
- [x] Live AST validation + (gated) sandbox execution
- [x] Security hardening: input limits, rate limiting, prompt-injection defence,
      sandbox gating, secret hygiene, CI dependency audit

## v1.2 — Quality & UX
- [ ] "Regenerate this framework only" buttons
- [ ] Copy-to-clipboard and per-result diffs (before/after critique)
- [ ] Token/cost usage display per generation

## v1.3 — More inputs
- [ ] Upload a requirements file (.md / .txt / .pdf)
- [ ] Parse user stories ("As a..., I want..., so that...")

## v2.0 — Smarter generation
- [ ] More providers (local Ollama, Anthropic) selectable in the UI
- [ ] Requirement → test traceability export (CSV/Excel)
- [ ] Optional stub-implementation generation so suites run fully green
- [ ] Estimated coverage % per requirement

## Stretch / research
- [ ] Mutation-testing score estimation for generated suites
- [ ] VS Code extension front-end
