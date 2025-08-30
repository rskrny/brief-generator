# app.py
# Streamlit application for the "Analyzer → Script Generator" pipeline
# using the new prompt builders and validators from prompts.py

import os
import json
import time
import traceback
from typing import Optional

import streamlit as st

# ---- LLM client (OpenAI) ----
# Works with openai>=1.0.0 SDK. Set OPENAI_API_KEY in your env or .streamlit/secrets.toml
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

# ---- Local imports ----
from prompts import (
    build_analyzer_messages,
    build_script_generator_messages,
    validate_analyzer_json,
    validate_script_json,
    default_product_facts,
    default_brand_voice,
)

# =========================
# Utility: OpenAI wrapper
# =========================
def get_openai_client() -> Optional["OpenAI"]:
    """
    Returns an OpenAI client if the SDK is installed and key present, else None.
    """
    if not _OPENAI_AVAILABLE:
        return None
    api_key = os.getenv("OPENAI_API_KEY", None) or st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception:
        return None


def call_openai_json(messages, model="gpt-4o-mini", temperature=0.2, max_retries=3, retry_base=1.5) -> str:
    """
    Calls OpenAI chat completions API, returning message.content as JSON string.
    Enforces JSON mode via response_format={"type": "json_object"}.
    """
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OpenAI client not available. Install 'openai' and set OPENAI_API_KEY.")

    last_err = None
    for i in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
            time.sleep(retry_base * (i + 1))
    raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_err}")


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="Brief Generator (Director Mode)", layout="wide")
st.title("🎬 Brief Generator — Director Mode")

with st.sidebar:
    st.header("LLM Settings")
    model = st.selectbox(
        "OpenAI Model",
        options=[
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
        ],
        index=0,
        help="Uses JSON response mode automatically."
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
# Actions
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

            with st.spinner("Analyzing reference video like a director…"):
                analyzer_json_str = call_openai_json(
                    messages=messages, model=model, temperature=temperature
                )

            # Parse + validate
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

                with st.spinner("Authoring brand-safe, scene-by-scene script…"):
                    script_json_str = call_openai_json(
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

st.caption(
    "Tip: keep transcripts/SRT accurate and add OCR keyframes for better on-screen text capture "
    "and edit beat detection. Then map the Script JSON to your storyboard exporter."
)
