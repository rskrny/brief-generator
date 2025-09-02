# app.py
# Brief Generator — Director Mode (Gemini Only)
# - Uses Streamlit Cloud Secrets for GOOGLE_API_KEY (fallback to env var locally)
# - Analyzer → Script Generator pipeline with JSON-only responses
# - Slim default UI; advanced inputs in an expander
# - Markdown brief export

import os
import json
import time
import traceback
from typing import Optional, List, Dict
import base64

import streamlit as st
import google.generativeai as genai

from prompts import (
    build_analyzer_messages,
    build_script_generator_messages,
    build_product_research_messages,
    validate_analyzer_json,
    validate_script_json,
)
from document_generator import brief_from_json_strings, make_brief_pdf
from web_utils import fetch_product_page_text


# =========================
# Key loading (Cloud-first)
# =========================
def _normalize_key(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    return v or None


def _get_google_api_key() -> str:
    """
    Always try Streamlit Cloud Secrets first (correct source on share.streamlit.io).
    Fallback to environment variable only for local runs.
    """
    # Streamlit Cloud secrets
    try:
        key = st.secrets["GOOGLE_API_KEY"]  # type: ignore[index]
        key = _normalize_key(key)
        if key:
            return key
    except Exception:
        pass

    # Local fallback (developer machine)
    key = _normalize_key(os.getenv("GOOGLE_API_KEY"))
    if key:
        return key

    raise RuntimeError(
        "GOOGLE_API_KEY not found.\n"
        "• On Streamlit Cloud: set it in the app's Settings → Secrets as: GOOGLE_API_KEY = \"your-key\"\n"
        "• Locally: create .streamlit/secrets.toml or set the environment variable before running."
    )


def _ensure_gemini_configured():
    key = _get_google_api_key()
    genai.configure(api_key=key)


# =========================
# Gemini call (JSON only)
# =========================
def _messages_to_single_prompt(messages: List[Dict[str, str]]) -> str:
    """Convert OpenAI-style messages into a single Gemini prompt string."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"[{role.upper()}]\n{content}\n")
    return "\n".join(parts).strip()


class EmptyGeminiResponseError(RuntimeError):
    """Raised when Gemini returns an empty response."""


def call_gemini_json(
    messages: List[Dict[str, str]],
    model: str = "gemini-1.5-pro",
    temperature: float = 0.2,
    max_retries: int = 3,
    retry_base: float = 1.5,
    max_output_tokens: int = 4096,
) -> str:
    """Calls Gemini and returns a JSON string (we request application/json)."""
    _ensure_gemini_configured()
    prompt_text = _messages_to_single_prompt(messages)
    last_err = None
    for i in range(max_retries):
        try:
            mdl = genai.GenerativeModel(model)
            resp = mdl.generate_content(
                prompt_text,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                    "max_output_tokens": max_output_tokens,
                },
            )
            if not resp.text:
                raise EmptyGeminiResponseError("Gemini returned no text")
            return resp.text
        except Exception as e:
            last_err = e
            time.sleep(retry_base * (i + 1))
    raise RuntimeError(f"Gemini call failed after {max_retries} retries: {last_err}")


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="Brief Generator — Director Mode (Gemini)", layout="wide")
st.title("🎬 Brief Generator — Director Mode (Gemini Only)")

with st.sidebar:
    st.header("Gemini")
    model = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"], index=1)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

    st.markdown("---")
    st.subheader("Platform / Runtime")
    platform = st.selectbox("Platform", ["tiktok", "reels", "ytshorts"], index=0)
    target_runtime_s = st.slider("Target Runtime (s)", 7, 60, 20, 1)

# Diagnostics (to confirm key is visible on Cloud)
with st.expander("🔧 Diagnostics (API Key)", expanded=False):
    try:
        vis = False
        masked = "(not found)"
        try:
            key = _normalize_key(st.secrets.get("GOOGLE_API_KEY", None))  # type: ignore[attr-defined]
            if key:
                vis = True
                masked = f"{key[:4]}…{key[-4:]}" if len(key) >= 8 else "(present)"
        except Exception:
            pass
        st.write("GOOGLE_API_KEY visible via st.secrets?", vis)
        st.write("Key (masked):", masked)
        st.caption("On Streamlit Cloud, set in Settings → Secrets. Locally, set env var or .streamlit/secrets.toml.")
    except Exception as e:
        st.error(f"Diagnostics error: {e}")

st.markdown(
    "This app runs a two-step pipeline: **Analyzer** → **Script Generator**. "
    "Analyzer produces a director-grade breakdown (scenes, on-screen text, influencer DNA, edit beats). "
    "Script Generator adapts that structure to your brand/product with claim-safe copy."
)

# ========== Inputs ==========
st.header("1) Reference (keep it simple)")
colA, colB = st.columns([2, 1])
with colA:
    video_url = st.text_input("Reference video URL (optional)", value="", placeholder="https://...")
with colB:
    duration_s = st.number_input("Duration (s, optional)", min_value=0.0, value=0.0, step=0.1)

with st.expander("Advanced evidence (optional: improves accuracy)"):
    col1, col2, col3 = st.columns(3)
    with col1:
        transcript_txt = st.text_area("Transcript (ASR text)", height=140, placeholder="Paste transcript…")
    with col2:
        srt_txt = st.text_area("Auto captions SRT/VTT", height=140, placeholder="Paste SRT/VTT…")
    with col3:
        ocr_json_str = st.text_area(
            "OCR keyframes JSON",
            height=140,
            placeholder='{"frames":[{"t":0.0,"text":["Replying to @..."]},{"t":1.6,"text":["Crystal-clear calls"]}]}',
        )

st.markdown("---")
st.header("2) Target Product Facts")
brand_name = st.text_input("Brand", value="", placeholder="Enter brand name")
product_name = st.text_input("Product", value="", placeholder="Enter product name")
product_page_url = st.text_input("Product page URL", value="", placeholder="https://…")

if "claims_text" not in st.session_state:
    st.session_state["claims_text"] = ""
if "forbidden_text" not in st.session_state:
    st.session_state["forbidden_text"] = (
        "medical/health claims without substantiation\n"
        "superlatives without proof\n"
        "comparative claims without head-to-head evidence"
    )
if "disclaimers_text" not in st.session_state:
    st.session_state["disclaimers_text"] = ""
if "product_page_text" not in st.session_state:
    st.session_state["product_page_text"] = ""

if st.button("🔍 Research product facts"):
    if brand_name.strip() and product_name.strip():
        page_text = ""
        if product_page_url.strip():
            try:
                page_text = fetch_product_page_text(product_page_url.strip())
                st.session_state["product_page_text"] = page_text
            except Exception as e:
                st.session_state["product_page_text"] = ""
                st.warning(f"Failed to fetch product page: {e}")
        else:
            st.session_state["product_page_text"] = ""
        try:
            messages = build_product_research_messages(
                brand_name.strip(),
                product_name.strip(),
                page_text=page_text or None,
            )
            with st.spinner("Researching product facts…"):
                research_json = call_gemini_json(messages=messages, model=model, temperature=temperature)
            try:
                data = json.loads(research_json)
                st.session_state["product_research"] = data
                approved_claims_list = data.get("approved_claims", []) or []
                forbidden_list = data.get("forbidden", []) or []
                disclaimers_list = data.get("required_disclaimers", []) or []

                st.session_state["claims_text"] = "\n".join(approved_claims_list)
                st.session_state["forbidden_text"] = "\n".join(forbidden_list)
                st.session_state["disclaimers_text"] = "\n".join(disclaimers_list)

                if approved_claims_list or forbidden_list or disclaimers_list:
                    st.info("Review and verify the claims below before proceeding.")
                else:
                    st.warning("No product facts found; verify the URL or enter claims manually.")
            except Exception:
                st.error("Research returned invalid JSON")
        except EmptyGeminiResponseError:
            st.warning("No facts were retrieved from Gemini. Please try again.")
        except Exception as e:
            st.error(f"Product research failed: {e}")
    else:
        st.warning("Enter brand and product first.")

claims_text = st.text_area(
    "Approved claims (whitelist, one per line)",
    height=120,
    key="claims_text",
    placeholder="List approved claims, one per line",
)

st.caption("Verify the factual accuracy of these claims before proceeding.")

if st.session_state.get("product_page_text"):
    with st.expander("Product page text (debug)", expanded=False):
        st.text(st.session_state["product_page_text"])

with st.expander("Advanced brand controls"):
    forbidden_text = st.text_area(
        "Forbidden claims",
        height=80,
        key="forbidden_text",
    )
    disclaimers_text = st.text_area("Required disclaimers", height=60, key="disclaimers_text")
    tone = st.text_input("Voice tone", value="conversational, direct, confident; no hype; no cringe")
    must_include = st.text_area("Must-include phrases (one per line)", value="")
    avoid_words = st.text_area("Avoid words (one per line)", value="insane\nultimate\nbest ever")
    cta_variant_text = st.text_area(
        "Preferred CTA variants",
        height=60,
        value="Check out our TikTok Shop. They're on sale right now.\nTap to see options and pricing.",
    )

# Build packets
research_packet = st.session_state.get("product_research", {})

# Build packets (use editable text areas so users can modify research results)
approved_claims = [x.strip() for x in claims_text.splitlines() if x.strip()]
forbidden_claims = [x.strip() for x in forbidden_text.splitlines() if x.strip()]
required_disclaimers = [x.strip() for x in disclaimers_text.splitlines() if x.strip()]
cta_variants = [x.strip() for x in cta_variant_text.splitlines() if x.strip()]

brand_value = research_packet.get("brand") or brand_name.strip()
product_name_value = research_packet.get("product_name") or product_name.strip()

brand_voice = {
    "tone": (tone if 'tone' in locals() else "conversational, direct, confident; no hype; no cringe"),
    "must_include": [x.strip() for x in (must_include.splitlines() if 'must_include' in locals() else []) if x.strip()],
    "avoid": [x.strip() for x in (avoid_words.splitlines() if 'avoid_words' in locals() else []) if x.strip()],
}

product_facts = {
    "brand": brand_value,
    "product_name": product_name_value,
    "approved_claims": approved_claims,
    "forbidden": forbidden_claims,
    "required_disclaimers": required_disclaimers,
}

# ========== State ==========
if "analyzer_json_str" not in st.session_state:
    st.session_state["analyzer_json_str"] = ""
if "analyzer_parsed" not in st.session_state:
    st.session_state["analyzer_parsed"] = None
if "script_json_str" not in st.session_state:
    st.session_state["script_json_str"] = ""
if "script_parsed" not in st.session_state:
    st.session_state["script_parsed"] = None

st.markdown("---")
analyze_col, script_col = st.columns(2)

# ---- Analyzer ----
with analyze_col:
    if st.button("🔎 Run Analyzer", use_container_width=True):
        try:
            messages = build_analyzer_messages(
                platform=platform,
                duration_s=(duration_s if duration_s > 0 else None),
                transcript=(locals().get("transcript_txt") or None),
                auto_captions_srt=(locals().get("srt_txt") or None),
                ocr_keyframes_json=(locals().get("ocr_json_str") or None),
                video_url=(video_url or None),
                aspect_ratio="9:16",
                fps_estimate=None,
            )

            with st.spinner("Analyzing reference video (Gemini)…"):
                analyzer_json_str = call_gemini_json(messages=messages, model=model, temperature=temperature)

            analyzer_parsed = json.loads(analyzer_json_str)
            errs = validate_analyzer_json(analyzer_parsed)

            st.session_state["analyzer_json_str"] = analyzer_json_str
            st.session_state["analyzer_parsed"] = analyzer_parsed

            if errs:
                st.error("Analyzer JSON issues:\n- " + "\n- ".join(errs))
            else:
                st.success("Analyzer JSON looks good ✅")

        except Exception as e:
            st.error(f"Analyzer failed: {e}")
            st.code(traceback.format_exc())

# ---- Script Generator ----
with script_col:
    if st.button("🎬 Generate Script from Analysis", use_container_width=True):
        try:
            if not st.session_state["analyzer_json_str"]:
                st.warning("Run the Analyzer first.")
            else:
                messages = build_script_generator_messages(
                    analyzer_json=st.session_state["analyzer_json_str"],
                    product_facts=product_facts,
                    brand_voice=brand_voice,
                    target_runtime_s=int(target_runtime_s),
                    platform=platform,
                    cta_variants=(cta_variants or None),
                )

                with st.spinner("Authoring scene-by-scene script (Gemini)…"):
                    script_json_str = call_gemini_json(messages=messages, model=model, temperature=temperature)

                script_parsed = json.loads(script_json_str)
                serrs = validate_script_json(script_parsed, target_runtime_s=target_runtime_s)

                st.session_state["script_json_str"] = script_json_str
                st.session_state["script_parsed"] = script_parsed

                if serrs:
                    st.warning("Script JSON warnings:\n- " + "\n- ".join(serrs))
                else:
                    st.success("Script JSON ready ✅")

        except Exception as e:
            st.error(f"Script generation failed: {e}")
            st.code(traceback.format_exc())

# ========== Output / Export ==========
st.markdown("---")
col_out_a, col_out_b = st.columns(2)
with col_out_a:
    st.subheader("Analyzer JSON")
    if st.session_state["analyzer_parsed"] is not None:
        st.json(st.session_state["analyzer_parsed"])
        st.download_button(
            "⬇️ Download analyzer.json",
            data=st.session_state["analyzer_json_str"].encode("utf-8"),
            file_name="analyzer.json",
            mime="application/json",
        )
    else:
        st.info("Run the Analyzer to see results here.")

with col_out_b:
    st.subheader("Script JSON")
    if st.session_state["script_parsed"] is not None:
        st.json(st.session_state["script_parsed"])
        st.download_button(
            "⬇️ Download script.json",
            data=st.session_state["script_json_str"].encode("utf-8"),
            file_name="script.json",
            mime="application/json",
        )
    else:
        st.info("Generate the script to see results here.")

st.markdown("---")
st.subheader("📄 Export Brief")
if st.session_state["analyzer_json_str"] and st.session_state["script_json_str"]:
    md = brief_from_json_strings(
        analyzer_json_str=st.session_state["analyzer_json_str"],
        script_json_str=st.session_state["script_json_str"],
        product_facts=product_facts,
        title="AI-Generated Influencer Brief (Director Mode)",
    )
    orientation_choice = st.selectbox(
        "PDF orientation",
        ["Auto", "Portrait", "Landscape"],
        index=0,
    )
    orientation_arg = None
    if orientation_choice == "Portrait":
        orientation_arg = "P"
    elif orientation_choice == "Landscape":
        orientation_arg = "L"

    pdf_bytes = make_brief_pdf(
        analyzer=st.session_state["analyzer_parsed"],
        script=st.session_state["script_parsed"],
        product_facts=product_facts,
        title="AI-Generated Influencer Brief (Director Mode)",
        orientation=orientation_arg,
    )
    st.download_button(
        "⬇️ Download brief.md",
        data=md.encode("utf-8"),
        file_name="brief.md",
        mime="text/markdown",
    )
    st.download_button(
        "⬇️ Download brief.pdf",
        data=pdf_bytes,
        file_name="brief.pdf",
        mime="application/pdf",
    )
    with st.expander("Preview Markdown", expanded=False):
        st.markdown(md)
    with st.expander("Preview PDF", expanded=False):
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
else:
    st.info("Run Analyzer and Script to export a brief.")
