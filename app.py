# app.py
# Streamlit application for the "Analyzer → Script Generator" pipeline
# Gemini-only implementation (google-generativeai).
# Uses prompts.py to build prompts and document_generator.py to export a Markdown brief.

import os
import json
import time
import traceback
from typing import Optional, List, Dict

import streamlit as st
import google.generativeai as genai

from prompts import (
    build_analyzer_messages,
    build_script_generator_messages,
    validate_analyzer_json,
    validate_script_json,
)
from document_generator import brief_from_json_strings


# =========================
# Gemini helpers
# =========================
def _get_google_api_key() -> Optional[str]:
    """Return GOOGLE_API_KEY from env or streamlit secrets."""
    key = os.getenv("GOOGLE_API_KEY")
    if not key and hasattr(st, "secrets"):
        key = st.secrets.get("GOOGLE_API_KEY", None)  # type: ignore[attr-defined]
    return key


def _ensure_gemini_configured():
    key = _get_google_api_key()
    if not key:
        raise RuntimeError(
            "GOOGLE_API_KEY not set. Use environment variable or .streamlit/secrets.toml"
        )
    genai.configure(api_key=key)


def _messages_to_single_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Convert OpenAI-style messages into a single Gemini prompt string.
    We keep role markers so system intent isn't lost.
    """
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"[{role.upper()}]\n{content}\n")
    return "\n".join(parts).strip()


def call_gemini_json(messages: List[Dict[str, str]], model: str = "gemini-1.5-pro", temperature: float = 0.2,
                     max_retries: int = 3, retry_base: float = 1.5) -> str:
    """
    Calls Gemini with a single text prompt and requests JSON output.
    Returns a JSON string (model is instructed to output JSON only).
    """
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
                    "response_mime_type": "application/json"
                }
            )
            # google-generativeai returns .text for textual content
            return resp.text or "{}"
        except Exception as e:
            last_err = e
            time.sleep(retry_base * (i + 1))
    raise RuntimeError(f"Gemini call failed after {max_retries} retries: {last_err}")


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="Brief Generator (Director Mode, Gemini)", layout="wide")
st.title("🎬 Brief Generator — Director Mode (Gemini Only)")

with st.sidebar:
    st.header("Gemini Settings")
    model = st.selectbox(
        "Gemini Model",
        options=["gemini-1.5-flash", "gemini-1.5-pro"],
        index=1,
        help="Model outputs JSON (we enforce application/json)."
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

    st.markdown("---")
    st.subheader("Runtime / Platform")
    platform = st.selectbox("Platform", ["tiktok", "reels", "ytshorts"], index=0)
    target_runtime_s = st.slider("Target Runtime (seconds)", 7, 60, 20, 1)
    aspect_ratio = st.text_input("Aspect Ratio", value="9:16")
    fps_hint = st.number_input("FPS (optional hint)", value=0, min_value=0, max_value=120, step=1)

    st.markdown("---")
    st.subheader("Brand Voice Settings (optional)")
    tone = st.text_input("Tone", value="conversational, direct, confident; no hype; no cringe")
    must_include = st.text_area("Must include (one per line)", value="")
    avoid_words = st.text_area("Avoid words (one per line)", value="insane\nultimate\nbest ever")

st.markdown(
    "This app runs a two-step pipeline: **Analyzer** → **Script Generator**. "
    "The Analyzer produces a director-grade breakdown (scenes, on-screen text, influencer DNA, edit beats). "
    "The Script Generator adapts that structure to your brand/product with claim-safe copy."
)

# =========================
# Inputs Section
# =========================
st.header("1) Reference Video Evidence (for Analyzer)")

colA, colB, colC = st.columns(3)

with colA:
    video_url = st.text_input("Reference video URL (optional)", value="", placeholder="https://...")
    duration_s = st.number_input("Video duration (seconds, if known)", min_value=0.0, value=0.0, step=0.1)

with colB:
    transcript_txt = st.text_area("Transcript text (optional)", height=140, placeholder="Paste ASR transcript...")

with colC:
    srt_txt = st.text_area("Auto captions SRT/VTT (optional)", height=140, placeholder="Paste SRT/VTT text...")

ocr_json_str = st.text_area(
    "OCR keyframes JSON (optional)",
    height=120,
    placeholder='{"frames":[{"t":0.0,"text":["Replying to @..."]}]}'
)

st.markdown("---")
st.header("2) Target Product Facts (for Script Generator)")

brand_name = st.text_input("Brand", value="SIAWAG")
product_name = st.text_input("Product", value="BTW73")

claims_text = st.text_area(
    "Approved claims (whitelist, one per line)",
    height=120,
    value="15+ years producing quality audio products\nBluetooth 5.4\nENC for clearer calls\nIPX5 water-resistant\nFast charging",
    help="Only these claims will be used by the Script Generator."
)

forbidden_text = st.text_area(
    "Forbidden claims (one per line)",
    height=90,
    value="medical/health claims without substantiation\nsuperlatives without proof\ncomparative claims without head-to-head evidence"
)

disclaimers_text = st.text_area(
    "Required disclaimers (one per line, optional)",
    height=60,
    value=""
)

cta_variant_text = st.text_area(
    "Preferred CTA variants (one per line, optional)",
    height=60,
    value="Check out our TikTok Shop. They're on sale right now.\nTap to see options and pricing."
)

# Construct brand voice dict
brand_voice = {
    "tone": tone,
    "must_include": [x.strip() for x in must_include.splitlines() if x.strip()],
    "avoid": [x.strip() for x in avoid_words.splitlines() if x.strip()],
}

# Construct product facts dict
approved_claims = [x.strip() for x in claims_text.splitlines() if x.strip()]
forbidden_claims = [x.strip() for x in forbidden_text.splitlines() if x.strip()]
required_disclaimers = [x.strip() for x in disclaimers_text.splitlines() if x.strip()]
cta_variants = [x.strip() for x in cta_variant_text.splitlines() if x.strip()]

product_facts = {
    "brand": brand_name.strip(),
    "product_name": product_name.strip(),
    "approved_claims": approved_claims,
    "forbidden": forbidden_claims,
    "required_disclaimers": required_disclaimers
}

# =========================
# Actions & State
# =========================
st.markdown("---")
analyze_col, script_col = st.columns([1, 1])

if "analyzer_json_str" not in st.session_state:
    st.session_state["analyzer_json_str"] = ""
if "analyzer_parsed" not in st.session_state:
    st.session_state["analyzer_parsed"] = None
if "script_json_str" not in st.session_state:
    st.session_state["script_json_str"] = ""
if "script_parsed" not in st.session_state:
    st.session_state["script_parsed"] = None

# ---- Analyzer button ----
with analyze_col:
    if st.button("🔎 Run Analyzer", use_container_width=True):
        try:
            messages = build_analyzer_messages(
                platform=platform,
                duration_s=(duration_s if duration_s > 0 else None),
                transcript=(transcript_txt or None),
                auto_captions_srt=(srt_txt or None),
                ocr_keyframes_json=(ocr_json_str or None),
                video_url=(video_url or None),
                aspect_ratio=aspect_ratio,
                fps_estimate=(int(fps_hint) if fps_hint else None),
            )

            with st.spinner("Analyzing reference video like a director (Gemini)…"):
                analyzer_json_str = call_gemini_json(
                    messages=messages, model=model, temperature=temperature
                )

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

# ---- Script button ----
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
                    cta_variants=cta_variants or None
                )

                with st.spinner("Authoring brand-safe, scene-by-scene script (Gemini)…"):
                    script_json_str = call_gemini_json(
                        messages=messages, model=model, temperature=temperature
                    )

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

# =========================
# Output / Inspection
# =========================
st.markdown("---")
outA, outB = st.columns(2)

with outA:
    st.subheader("Analyzer JSON (Director Breakdown)")
    if st.session_state["analyzer_parsed"] is not None:
        st.json(st.session_state["analyzer_parsed"])
        st.download_button(
            "⬇️ Download analyzer.json",
            data=st.session_state["analyzer_json_str"].encode("utf-8"),
            file_name="analyzer.json",
            mime="application/json"
        )
    else:
        st.info("Run the Analyzer to see results here.")

with outB:
    st.subheader("Script JSON (Storyboard-Ready)")
    if st.session_state["script_parsed"] is not None:
        st.json(st.session_state["script_parsed"])
        st.download_button(
            "⬇️ Download script.json",
            data=st.session_state["script_json_str"].encode("utf-8"),
            file_name="script.json",
            mime="application/json"
        )
    else:
        st.info("Generate the script to see results here.")

# =========================
# Export Brief (Markdown)
# =========================
st.markdown("---")
st.subheader("📄 Export Brief (Markdown)")
if st.session_state["analyzer_json_str"] and st.session_state["script_json_str"]:
    md = brief_from_json_strings(
        analyzer_json_str=st.session_state["analyzer_json_str"],
        script_json_str=st.session_state["script_json_str"],
        product_facts=product_facts,
        title="AI-Generated Influencer Brief (Director Mode)"
    )
    st.download_button(
        "⬇️ Download brief.md",
        data=md.encode("utf-8"),
        file_name="brief.md",
        mime="text/markdown"
    )
    with st.expander("Preview Markdown", expanded=False):
        st.markdown(md)
else:
    st.info("Run Analyzer and Script to export a brief.")

st.caption(
    "Tip: add accurate transcripts/SRT and OCR keyframes for better on-screen text capture "
    "and edit beat detection. Then use the Markdown brief for storyboard/PDF."
)
