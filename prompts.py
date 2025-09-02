# prompts.py
# Drop-in prompt builders for the "Analyzer → Script Generator" pipeline.
# These produce *messages* ready for OpenAI/Gemini chat APIs.
# The Analyzer outputs a director-grade JSON breakdown.
# The Script Generator consumes that JSON + product facts to produce a new script.
#
# Usage (example):
#   from prompts import build_analyzer_messages, build_script_generator_messages
#   messages = build_analyzer_messages(platform="tiktok", duration_s=19.7, ...)
#   # call LLM with messages
#
#   messages2 = build_script_generator_messages(
#       analyzer_json=analyzer_output_json_string,
#       product_facts=..., brand_voice=..., target_runtime_s=20
#   )

from textwrap import dedent
import json


# ----------------------------
# Global constants / schemas
# ----------------------------

ANALYZER_JSON_SCHEMA = dedent("""
{
  "video_metadata": {
    "platform": "tiktok|reels|ytshorts",
    "duration_s": 0,
    "fps_estimate": 30,
    "aspect_ratio": "9:16"
  },
  "global_style": {
    "hook_type": ["pattern_interrupt","reply_to_comment","myth_bust","before_after","demo"],
    "promise": "",
    "payoff": "",
    "cta_core": "",
    "edit_grammar": {
      "avg_cut_interval_s": 0.0,
      "transition_types": ["hard_cut","jump_cut","speed_ramp","match_cut"],
      "broll_ratio": 0.0,
      "overlay_density_per_10s": 0
    },
    "music": {"genre":"", "bpm": 0, "mood":[]},
    "risk_flags": []
  },
  "influencer_DNA": {
    "persona_tags": [],
    "energy_1to5": 3,
    "pace": "staccato|flowing",
    "sentiment_arc": [],
    "delivery": {
      "POV":"talking_head|vlog_walk|overhead_demo",
      "eye_contact_pct": 0,
      "gesture_style": "",
      "rhetoric": []
    },
    "editing_style": {
      "cuts":"",
      "text_style":"",
      "anim": [],
      "color_grade":""
    }
  },
  "beats": [
    {"t": 0.0, "type": "cut|hook|punch|cta|reveal", "note": ""}
  ],
  "scenes": [
    {
      "idx": 1,
      "start_s": 0.0,
      "end_s": 0.0,
      "shot": "",
      "lens_feel": "",
      "camera": "",
      "framing": "",
      "location": "",
      "lighting": "",
      "action": "",
      "dialogue_vo": "",
      "captions_text": "",
      "on_screen_text": [
        {"text": "", "t_in": 0.0, "t_out": 0.0, "position": "", "style": ""}
      ],
      "sfx": [],
      "music_moment": "",
      "transition_out": "",
      "retention_device": [],
      "product_focus": "",
      "disclaimer": null
    }
  ],
  "compliance": {
    "forbidden_claims": [],
    "required_disclaimers": []
  },
  "transferable_patterns": {
    "must_keep": [],
    "rewrite": []
  }
}
""").strip()


SCRIPT_JSON_SCHEMA = dedent("""
{
  "target_runtime_s": 20,
  "script": {
    "opening_hook": {
      "start_s": 0.0,
      "end_s": 0.0,
      "dialogue": "",
      "on_screen_text": [
        {"text":"", "t_in":0.0, "t_out":0.0, "position":"", "style":""}
      ],
      "visual": "",
      "retention_device": []
    },
    "scenes": [
      {
        "idx": 1,
        "start_s": 0.0,
        "end_s": 0.0,
        "shot": "",
        "lens_feel": "",
        "camera": "",
        "framing": "",
        "location": "",
        "lighting": "",
        "action": "",
        "dialogue_vo": "",
        "on_screen_text": [
          {"text":"", "t_in":0.0, "t_out":0.0, "position":"", "style":""}
        ],
        "sfx": [],
        "music_moment": "",
        "transition_out": "",
        "retention_device": [],
        "product_focus": "",
        "disclaimer": null
      }
    ],
    "cta_options": [
      {
        "variant":"A",
        "dialogue":"",
        "on_screen_text": [],
        "visual":"",
        "transition":""
      },
      {
        "variant":"B",
        "dialogue":"",
        "on_screen_text": [],
        "visual":"",
        "transition":"loop_back_to_scene_1"
      }
    ]
  },
  "notes_for_legal": [],
  "checklist": {
    "forbidden_claims_present": false,
    "brand_terms_ok": true,
    "captions_safe_area_ok": true
  }
}
""").strip()


ANALYZER_SYSTEM_PREAMBLE = dedent("""
You are a Film Director + Editor + Script Supervisor analyzing a short-form video to produce a director-ready breakdown. 
Think step-by-step, but OUTPUT MUST BE JSON ONLY and must match the provided schema exactly. 
If you cannot verify a field, set a safe default or null. Do not invent on-screen text.
""").strip()

ANALYZER_USER_INSTRUCTIONS = dedent(f"""
Return ONLY valid JSON adhering to this schema:

{ANALYZER_JSON_SCHEMA}

Rules:
1) Do NOT hallucinate on-screen text. If unknown, use [] for "on_screen_text" in that scene.
2) Every scene must include: start_s, end_s, shot, camera, framing, action, dialogue_vo (or ""), music_moment, transition_out, retention_device.
3) Populate influencer_DNA from delivery evidence: persona_tags, energy_1to5, pace, rhetoric, eye_contact_pct.
4) Create a "beats" array marking hooks, emphatic punches, reveals, and CTA entries by timestamp.
5) Note compliance risks in "compliance.forbidden_claims".
6) Durations must be consistent; last scene end_s equals video duration.
7) OUTPUT JSON ONLY. No markdown. No commentary.
""").strip()


SCRIPT_SYSTEM_PREAMBLE = dedent("""
You are a Creative Director + AD + Copy Chief. 
Consume the Analyzer JSON and author a NEW script for the TARGET product/brand. 
Think step-by-step, but OUTPUT MUST BE JSON ONLY and must match the provided schema exactly. 
""").strip()

SCRIPT_USER_INSTRUCTIONS_TEMPLATE = dedent(f"""
You will create a new short-form video script and shot plan using the reference Analyzer JSON.

Schema to return (JSON only):
{SCRIPT_JSON_SCHEMA}

Constraints:
- Preserve only transferable_patterns.must_keep; rewrite everything else for TARGET.
- All claims must come from the provided whitelist; otherwise propose alternates in "notes_for_legal".
- Timing must fit the requested runtime ±0.5s.
- Each scene must include: action, exact dialogue/VO, exact on-screen text (2-line max, ~7–10 words per line), shot & camera move, transitions, SFX, music cues, and a reason-to-watch in the first 3s.
- Provide two endings: (A) hard CTA, (B) soft loop (transition 'loop_back_to_scene_1').
- OUTPUT JSON ONLY. No markdown. No commentary.
""").strip()


# ----------------------------
# Helper: compact product facts
# ----------------------------

def _pack_product_facts(product_facts: dict) -> str:
    """
    Convert product facts/claims into a compact JSON block the model can quote from.
    Expect keys like: "brand", "product_name", "approved_claims" (list of strings), "forbidden" (list),
    "required_disclaimers" (list), "voice_rules" (dict), etc.
    """
    try:
        return json.dumps(product_facts, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        # Fall back to a defensive string if serialization fails.
        return str(product_facts)


# ----------------------------
# Public builders (Analyzer)
# ----------------------------

def build_analyzer_messages(
    *,
    platform: str = "tiktok",
    duration_s: float | None = None,
    transcript: str | None = None,
    auto_captions_srt: str | None = None,
    ocr_keyframes_json: str | None = None,
    video_url: str | None = None,
    aspect_ratio: str = "9:16",
    fps_estimate: int | None = None
):
    """
    Returns a messages list suitable for chat completion APIs.
    Provide whatever inputs you have: transcript, SRT, OCR JSON, or just a URL.
    The prompt forbids hallucinating on-screen text; unknowns must be [] or "".
    """
    # Build an inputs packet for the model (as JSON string).
    evidence = {
        "platform": platform,
        "duration_s_hint": duration_s,
        "aspect_ratio_hint": aspect_ratio,
        "fps_estimate_hint": fps_estimate,
        "video_url": video_url,
        "transcript": transcript,
        "auto_captions_srt": auto_captions_srt,
        "ocr_keyframes_json": ocr_keyframes_json
    }
    evidence_json = json.dumps(evidence, ensure_ascii=False)

    messages = [
        {"role": "system", "content": ANALYZER_SYSTEM_PREAMBLE},
        {
            "role": "user",
            "content": dedent(f"""
            Analyze the reference short-form video and produce a director-ready breakdown.
            Inputs (JSON):
            {evidence_json}

            {ANALYZER_USER_INSTRUCTIONS}
            """).strip()
        }
    ]
    return messages


# ----------------------------
# Public builders (Script Generator)
# ----------------------------

def build_script_generator_messages(
    *,
    analyzer_json: str,
    product_facts: dict,
    brand_voice: dict | None = None,
    target_runtime_s: int = 20,
    platform: str = "tiktok",
    cta_variants: list[str] | None = None
):
    """
    analyzer_json: string of EXACT Analyzer JSON output.
    product_facts: dict including 'brand', 'product_name', 'approved_claims', 'forbidden', 'required_disclaimers'.
    brand_voice: optional dict e.g., {"tone":"conversational, direct", "must_include":["brand name 'SIAWAG'"], "avoid":["hype words"]}
    cta_variants: optional list of CTA copy to prefer; the model still must produce two endings.
    """
    if cta_variants is None:
        cta_variants = [
            "Check out our TikTok Shop. They're on sale right now.",
            "Tap to see options and pricing."
        ]

    inputs_packet = {
        "platform": platform,
        "target_runtime_s": target_runtime_s,
        "analyzer_json": analyzer_json,
        "product_facts": product_facts,
        "brand_voice": brand_voice or {},
        "cta_variants": cta_variants
    }
    inputs_json = json.dumps(inputs_packet, ensure_ascii=False)

    # A stricter user message that forbids drifting from whitelist claims.
    user_msg = dedent(f"""
    Create a new short-form video plan for the TARGET brand/product using the Analyzer JSON.
    Inputs (JSON):
    {inputs_json}

    {SCRIPT_USER_INSTRUCTIONS_TEMPLATE}

    Additional rules:
    - Claims whitelist: product_facts.approved_claims ONLY.
    - If a necessary selling point is not in the whitelist, add a polite alternative to "notes_for_legal" and keep it OUT of dialogue/on-screen text.
    - Ensure readable on-screen text (2-line max, ~7–10 words/line) and place it in safe areas (top/bottom margins respected).
    - No superlatives ("best", "ultimate") unless product_facts contains substantiation.
    - Include brand name in dialogue at least once (if provided in product_facts.brand).
    """).strip()

    messages = [
        {"role": "system", "content": SCRIPT_SYSTEM_PREAMBLE},
        {"role": "user", "content": user_msg}
    ]
    return messages


# ----------------------------
# Public builder (Product Research)
# ----------------------------

def build_product_research_messages(brand: str, product: str):
    """Prompt the model to gather marketing-compliant product facts.

    Returns a messages list asking for JSON with three lists:
    - approved_claims: safe claims we can state
    - required_disclaimers: disclaimers that must accompany those claims
    - forbidden: risky claims to avoid

    The model must respond with JSON only; empty lists are allowed if
    information is unavailable.
    """

    user_content = dedent(
        f"""
        Research factual, legally compliant marketing claims for the
        product "{product}" from brand "{brand}".

        Return JSON with exactly these fields:
        - "approved_claims": list of short, substantiated marketing claims
        - "required_disclaimers": list of disclaimers required for those claims
        - "forbidden": list of risky or prohibited claims to avoid

        If unsure or no data, use empty lists. Output JSON only with no
        commentary or extra keys.
        """
    ).strip()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a compliance-focused marketing assistant. "
                "Respond with JSON only."
            ),
        },
        {"role": "user", "content": user_content},
    ]

    return messages


# ----------------------------
# Optional: tiny validators (client-side)
# ----------------------------

def validate_analyzer_json(parsed: dict) -> list[str]:
    """
    Lightweight checks to catch common LLM misses before downstream use.
    Returns list of error strings; empty if looks OK.
    """
    errs = []
    if "scenes" not in parsed or not isinstance(parsed["scenes"], list) or not parsed["scenes"]:
        errs.append("Analyzer JSON missing non-empty 'scenes'.")
    if "video_metadata" not in parsed:
        errs.append("Analyzer JSON missing 'video_metadata'.")
    else:
        vm = parsed["video_metadata"]
        if "duration_s" not in vm or not isinstance(vm["duration_s"], (int, float)):
            errs.append("'video_metadata.duration_s' missing or not numeric.")
    # Check last scene end equals duration (within 0.2s tolerance)
    try:
        duration = float(parsed["video_metadata"]["duration_s"])
        last_end = float(parsed["scenes"][-1]["end_s"])
        if abs(last_end - duration) > 0.2:
            errs.append(f"Last scene end_s ({last_end}) != duration_s ({duration}).")
    except Exception:
        pass
    return errs


def validate_script_json(parsed: dict, target_runtime_s: float | None = None) -> list[str]:
    """
    Lightweight checks for the generated script JSON.
    """
    errs = []
    try:
        if "script" not in parsed:
            errs.append("Script JSON missing 'script'.")
        else:
            scenes = parsed["script"].get("scenes", [])
            if not scenes:
                errs.append("'script.scenes' is empty.")
            else:
                if scenes[0]["start_s"] > 0.05:
                    errs.append("First scene should start at ~0.0s.")
        if target_runtime_s is not None:
            got = float(parsed.get("target_runtime_s", 0))
            if abs(got - float(target_runtime_s)) > 0.6:
                errs.append(f"target_runtime_s mismatch: got {got}, expected ~{target_runtime_s}.")
    except Exception:
        pass
    return errs


# ----------------------------
# Convenience presets
# ----------------------------

def default_product_facts(brand: str, product_name: str, approved_claims: list[str]) -> dict:
    """
    Starter utility for building the product facts packet.
    """
    return {
        "brand": brand,
        "product_name": product_name,
        "approved_claims": approved_claims,
        "forbidden": [
            "medical/health claims without substantiation",
            "superlatives without proof",
            "comparative claims without head-to-head evidence"
        ],
        "required_disclaimers": []
    }


def default_brand_voice() -> dict:
    """
    A neutral but TikTok-friendly voice rule set; adjust as needed.
    """
    return {
        "tone": "conversational, direct, confident; no hype; no cringe",
        "must_include": [],
        "avoid": ["insane", "ultimate", "best ever"]
    }
