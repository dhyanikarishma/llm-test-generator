"""LLM Test-Case Generator - Streamlit web app.

Run locally with:
    streamlit run app.py

Security highlights wired into this UI:
  * API keys are read server-side only (never shown to the browser).
  * User input is sanitized + length-capped before reaching the LLM.
  * A per-session sliding-window rate limit guards against cost attacks.
  * LLM output is rendered as escaped Markdown / code (no raw HTML => no XSS).
  * Executing generated code is disabled unless ENABLE_SANDBOX_RUN=1.
"""

from __future__ import annotations

import io
import time
import zipfile

import streamlit as st
from dotenv import load_dotenv

from src import config, security
from src.generator import generate
from src.llm_client import create_client
from src.models import GenerationOptions
from src.validation import run_pytest, validate_python_syntax

load_dotenv()

st.set_page_config(
    page_title="LLM Test-Case Generator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .hero {
        background: linear-gradient(120deg, #6C5CE7 0%, #8E7BFF 45%, #00CEC9 100%);
        padding: 2.2rem 2rem; border-radius: 18px; margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(108, 92, 231, 0.25);
      }
      .hero h1 { color: #fff; margin: 0; font-size: 2.1rem; font-weight: 800; letter-spacing: -0.5px; }
      .hero p { color: rgba(255,255,255,0.92); margin: 0.5rem 0 0 0; font-size: 1.02rem; }
      .pill { display: inline-block; background: rgba(255,255,255,0.18); color: #fff;
        padding: 4px 12px; border-radius: 999px; font-size: 0.78rem; margin-right: 8px; margin-top: 12px; }
      .stat-card { background: #1A1D29; border: 1px solid #2A2E3D; border-radius: 14px;
        padding: 1rem 1.2rem; text-align: center; }
      .stat-card .num { font-size: 1.6rem; font-weight: 800; color: #8E7BFF; }
      .stat-card .lbl { font-size: 0.8rem; color: #9AA0B4; }
      div.stButton > button, div.stDownloadButton > button {
        background: linear-gradient(120deg, #6C5CE7, #8E7BFF); color: #fff; border: none;
        border-radius: 12px; padding: 0.6rem 1rem; font-weight: 700;
        transition: transform 0.05s ease, box-shadow 0.2s ease; }
      div.stButton > button:hover, div.stDownloadButton > button:hover {
        box-shadow: 0 6px 18px rgba(108, 92, 231, 0.4); transform: translateY(-1px); }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,  # used ONLY for our own static CSS above, never for model output
)

st.markdown(
    """
    <div class="hero">
      <h1>🧪 LLM Test-Case Generator</h1>
      <p>Turn plain-English software specifications into runnable test suites &mdash;
         PyTest, Google Test (C++), and Robot Framework &mdash; with edge cases,
         negative tests, coverage analysis, a traceability matrix, and a
         self-critique pass.</p>
      <span class="pill">Multi-provider</span>
      <span class="pill">PyTest · GoogleTest · Robot</span>
      <span class="pill">Self-critique</span>
      <span class="pill">Traceability</span>
      <span class="pill">Secure by design</span>
    </div>
    """,
    unsafe_allow_html=True,
)

EXAMPLES: dict[str, str] = {
    "User Account Security": (
        "User Account Security\n"
        "- Users can reset their password through email verification.\n"
        "- Passwords must contain at least 8 characters.\n"
        "- Accounts lock after 5 consecutive failed login attempts."
    ),
    "Bearer Session Inactivity Timer (telecom)": (
        "Bearer Session Inactivity Timer\n"
        "- A data bearer is released after 30 minutes of inactivity.\n"
        "- Any uplink or downlink packet resets the inactivity timer.\n"
        "- The timer must not fire while a voice call is active on the bearer.\n"
        "- On timer expiry, a Delete Session Request is sent to the gateway."
    ),
    "API Rate Limiter": (
        "API Rate Limiter\n"
        "- Each API key may make 100 requests per minute.\n"
        "- Requests beyond the limit return HTTP 429.\n"
        "- The counter resets at the start of each minute window.\n"
        "- Admin keys are exempt from rate limiting."
    ),
    "Shopping Cart Checkout": (
        "Checkout\n"
        "- A cart must contain at least 1 item before checkout is allowed.\n"
        "- Orders over $50 qualify for free shipping.\n"
        "- A discount code reduces the total by 10%, one code per order.\n"
        "- Payment must be authorized before the order is confirmed."
    ),
}

# ---------------------------------------------------------------------------
# Sidebar: configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    provider = st.selectbox(
        "AI provider",
        list(config.PROVIDERS.keys()),
        format_func=lambda p: config.PROVIDERS[p]["label"],
    )
    meta = config.PROVIDERS[provider]

    api_key = config.get_api_key(provider)
    if api_key:
        st.success(f"{meta['label']} key detected ✅")
    else:
        st.error("No API key found for this provider")
        st.caption(f"Get a key at {meta['key_url']}, then add `{meta['env']}` to your `.env`.")

    model = st.selectbox("Model", meta["models"])

    st.divider()
    st.subheader("Target frameworks")
    selected: list[str] = []
    for key, fwmeta in config.FRAMEWORKS.items():
        if st.checkbox(fwmeta["label"], value=(key == "pytest"), key=f"fw_{key}"):
            selected.append(key)

    st.subheader("Test categories")
    include_edge = st.checkbox("Edge cases & boundaries", value=True)
    include_negative = st.checkbox("Negative tests", value=True)
    include_coverage = st.checkbox("Coverage suggestions", value=True)

    st.subheader("Advanced")
    self_critique = st.checkbox("Self-critique pass (AI improves its own tests)", value=False)
    traceability = st.checkbox("Requirement → test traceability matrix", value=True)

    st.divider()
    st.caption(
        f"🔒 Rate limit: {config.RATE_LIMIT_MAX_GENERATIONS} generations / "
        f"{config.RATE_LIMIT_WINDOW_SECONDS}s · input capped at "
        f"{config.MAX_SPEC_CHARS} chars."
    )
    st.caption("Built by an engineer with telecom software-validation experience.")

# ---------------------------------------------------------------------------
# Main input
# ---------------------------------------------------------------------------
left, right = st.columns([3, 1], gap="large")

with left:
    st.subheader("📋 Software specification")
    ex_col1, ex_col2 = st.columns([3, 1])
    with ex_col1:
        example_choice = st.selectbox(
            "Load an example", ["— none —"] + list(EXAMPLES.keys()), label_visibility="collapsed"
        )
    with ex_col2:
        if st.button("Load", use_container_width=True) and example_choice in EXAMPLES:
            st.session_state["spec_text"] = EXAMPLES[example_choice]

    spec = st.text_area(
        "Describe the feature, requirements, or rules to test:",
        value=st.session_state.get("spec_text", ""),
        height=220,
        max_chars=config.MAX_SPEC_CHARS,  # client-side cap (UX); server re-validates
        placeholder=EXAMPLES["User Account Security"],
        label_visibility="collapsed",
    )
    st.caption(f"{len(spec)} / {config.MAX_SPEC_CHARS} characters")

with right:
    st.subheader("ℹ️ Tips")
    st.markdown(
        "- One requirement per line works best.\n"
        "- Include numbers (limits, counts) for sharp edge cases.\n"
        "- Mention error behaviour for strong negative tests.\n"
        "- Turn on **self-critique** for higher quality (slower)."
    )

generate_clicked = st.button("🚀 Generate Tests", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Generation (with rate limiting)
# ---------------------------------------------------------------------------
if generate_clicked:
    history = st.session_state.get("gen_times", [])
    allowed, retry_after, history = security.check_rate_limit(history, time.time())

    if not api_key:
        st.error("Cannot generate without an API key for the selected provider. See the sidebar.")
    elif not spec.strip():
        st.warning("Please enter a specification first (or load an example).")
    elif not selected:
        st.warning("Select at least one target framework in the sidebar.")
    elif not allowed:
        st.error(f"⏳ Rate limit reached. Please wait {retry_after}s before generating again.")
    else:
        history.append(time.time())
        st.session_state["gen_times"] = history
        options = GenerationOptions(
            frameworks=selected,
            include_edge_cases=include_edge,
            include_negative_tests=include_negative,
            include_coverage=include_coverage,
            self_critique=self_critique,
            traceability=traceability,
        )
        try:
            client = create_client(provider, api_key, model)
            with st.spinner("Designing your test suite with AI..."):
                st.session_state["result"] = generate(spec, options, client)
        except Exception:  # noqa: BLE001
            # Generic message to the user; no stack trace / internal detail leaked.
            st.error("Something went wrong while contacting the model. Please try again.")


def _build_zip(result) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in result.framework_results:
            if r.code and not r.error:
                zf.writestr(r.filename, r.code)
        if result.analysis:
            zf.writestr("TEST_DESIGN.md", result.analysis)
        if result.traceability:
            zf.writestr("TRACEABILITY.md", result.traceability)
        zf.writestr("SPECIFICATION.txt", result.spec)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
result = st.session_state.get("result")
if result is not None:
    st.divider()

    for msg in result.errors:
        st.error(msg)

    if result.framework_results or result.analysis:
        c1, c2, c3, c4 = st.columns(4)
        n_ok = sum(1 for r in result.framework_results if r.code and not r.error)
        total_lines = sum(len(r.code.splitlines()) for r in result.framework_results if r.code)
        for col, num, lbl in (
            (c1, n_ok, "Frameworks generated"),
            (c2, total_lines, "Lines of test code"),
            (c3, "Yes" if result.analysis else "No", "Coverage analysis"),
            (c4, "Yes" if result.traceability else "No", "Traceability matrix"),
        ):
            col.markdown(
                f"<div class='stat-card'><div class='num'>{num}</div>"
                f"<div class='lbl'>{lbl}</div></div>",
                unsafe_allow_html=True,
            )

        st.write("")
        st.download_button(
            "⬇️ Download everything as .zip",
            data=_build_zip(result),
            file_name="generated_tests.zip",
            mime="application/zip",
        )
        st.write("")

        tab_labels: list[str] = []
        if result.analysis:
            tab_labels.append("🧭 Test Design & Coverage")
        tab_labels.extend(r.label for r in result.framework_results)
        if result.traceability:
            tab_labels.append("🔗 Traceability")
        tabs = st.tabs(tab_labels)

        idx = 0
        if result.analysis:
            with tabs[idx]:
                # Rendered as escaped Markdown (unsafe_allow_html defaults to False) => XSS-safe.
                st.markdown(result.analysis)
            idx += 1

        for r in result.framework_results:
            with tabs[idx]:
                if r.error:
                    st.error("Generation failed for this framework. Try again or pick another provider.")
                else:
                    st.code(r.code, language=r.language)
                    st.download_button(
                        f"⬇️ Download {r.filename}",
                        data=r.code,
                        file_name=r.filename,
                        mime="text/plain",
                        key=f"dl_{r.framework}",
                    )

                    if r.critique:
                        with st.expander("🔍 What the self-critique pass improved"):
                            st.markdown(r.critique)

                    if r.framework == "pytest":
                        st.markdown("##### ✅ Validation")
                        report = validate_python_syntax(r.code)
                        if report.ok:
                            st.success(
                                f"Valid Python · {report.num_tests} test function(s) · "
                                f"{report.num_asserts} assertion(s)"
                            )
                        else:
                            st.error(f"Syntax error → {report.error}")
                        for w in report.warnings:
                            st.warning(w)

                        if config.sandbox_run_enabled():
                            if st.button("▶️ Run this suite in a sandbox", key=f"run_{r.framework}"):
                                with st.spinner("Running pytest..."):
                                    run = run_pytest(r.code)
                                if not run.ran:
                                    st.error(run.error)
                                elif run.returncode == 0:
                                    st.success("All tests passed ✅")
                                    st.code(run.output, language="text")
                                else:
                                    st.warning(
                                        "Tests ran but did not all pass. This is expected when the "
                                        "suite references not-yet-implemented placeholder functions."
                                    )
                                    st.code(run.output, language="text")
                        else:
                            st.info(
                                "▶️ Sandbox execution is disabled for safety (it would run "
                                "AI-generated code). Enable locally with `ENABLE_SANDBOX_RUN=1`."
                            )
            idx += 1

        if result.traceability:
            with tabs[idx]:
                st.markdown(result.traceability)
            idx += 1
else:
    st.info("👈 Pick a provider, load or paste a spec, and click **Generate Tests**.")
