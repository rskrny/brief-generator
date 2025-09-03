# prompts.py
# Drop-in prompt builders for the "Analyzer → Script Generator" pipeline.
# These produce *messages* ready for OpenAI/Gemini chat APIs.
# The Analyzer outputs a director-grade JSON breakdown.
# The Script Generator consumes that JSON + product facts to produce a new script.

from textwrap import dedent
import json
from typing import Optional


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
    "video_category": "Unboxing|Tutorial|Skit|Challenge|Testimonial|Product-Demo|Day-in-the-Life",
    "narrative_structure": "Problem/Agitate/Solve|Before-and-After|Direct-Comparison|Myth-Busting|Storytelling-Hook",
    "hook_type": ["pattern_interrupt","reply_to_comment","myth_bust","before_after","demo"],
    "promise": "A clear statement of what the viewer will gain or learn.",
    "payoff": "The fulfillment of the promise made in the hook.",
    "cta_core": "The primary call to action.",
    "persuasion_tactics": ["Social-Proof","Scarcity","Authority","Demonstration","Urgency"],
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
    "persona": {
      "archetype": "The-Expert|The-Relatable-Friend|The-Entertainer|The-Aspirational-Figure",
      "communication_style": "Direct-and-Informative|Storytelling|Humorous|Energetic",
      "energy_1to5": 3
    },
    "pace": "staccato|flowing",
    "sentiment_arc": ["neutral","positive","excited"],
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
      "shot_type": "CU|MCU|MS|WS",
      "lens_feel": "Wide|Standard|Telephoto",
      "camera_movement": "Static|Handheld|Pan|Tilt|Dolly-Zoom",
      "shot_composition": "Rule-of-Thirds|Symmetrical|Leading-Lines",
      "framing": "Chest-up|Full-body|Head-and-shoulders",
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
  "transferable_patterns": {
    "must_keep": ["List the core structural elements that make this video work."],
    "rewrite": ["List elements specific to the original product/creator that should be replaced."]
  }
}
""").strip()


SCRIPT_JSON_SCHEMA = dedent("""
{
  "target_runtime_s": 20,
  "script": {
    "opening_hook": {
      "start_s": 0.0,
      "end_s": 3.0,
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
        "shot_type": "CU|MCU|MS|WS",
        "lens_feel": "Wide|Standard|Telephoto",
        "camera_movement": "Static|Handheld|Pan|Tilt|Dolly-Zoom",
        "shot_composition": "Rule-of-Thirds|Symmetrical|Leading-Lines",
        "framing": "Chest-up|Full-body|Head-and-shoulders",
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
You are an expert Film Director and Viral Marketing Strategist. Your task is to dissect a short-form video into a director-ready JSON breakdown.
Think step-by-step. Your analysis must be deep, identifying the underlying formulas that make the video successful.
OUTPUT MUST BE VALID JSON ONLY and must match the provided schema exactly. Do not add comments or markdown.
If you cannot verify a field, use a safe default, null, or an empty array.
""").strip()

ANALYZER_USER_INSTRUCTIONS = dedent(f"""
Return ONLY valid JSON adhering to this schema:

{ANALYZER_JSON_SCHEMA}

Rules:
1) Deconstruct the video's core logic. Identify its `video_category` and the `narrative_structure` it follows. List the specific `persuasion_tactics` used to engage the viewer.
2) Thoroughly profile the creator's on-screen character in the `influencer_DNA.persona` object. Define their `archetype` and `communication_style`.
3) For each scene, provide granular detail on the filmmaking itself: `camera_movement`, `shot_composition`, and other visual elements.
4. Ensure the last scene's end_s equals `video_metadata.duration_s`.
5. Identify the core reusable formula for success in `transferable_patterns.must_keep`.
6. OUTPUT JSON ONLY. No markdown. No commentary.
""").strip()


SCRIPT_SYSTEM_PREAMBLE = dedent("""
You are a Creative Director and expert Copywriter specializing in high-performing short-form video ads.
You will consume an Analyzer JSON of a successful reference video and use it to author a NEW script for a different product/brand.
Think step-by-step, but OUTPUT MUST BE VALID JSON ONLY and must match the provided schema exactly.
""").strip()

SCRIPT_USER_INSTRUCTIONS_TEMPLATE = dedent(f"""
You will create a new short-form video script and shot plan using the reference Analyzer JSON.

Schema to return (JSON only):
{SCRIPT_JSON_SCHEMA}

Constraints:
- **Replicate the Formula:** You MUST adopt the `narrative_structure`, `video_category`, `persuasion_tactics`, and `influencer_DNA.persona` from the analysis. The goal is to recreate the *formula* of the successful video, not its literal content.
- **Use Transferable Patterns:** Build your script around the `transferable_patterns.must_keep` identified in the analysis.
- **Claim-Safe Copy:** All product claims in dialogue or on-screen text MUST come from the provided `product_facts.approved_claims` whitelist.
- **Adhere to Timing:** The total runtime must match the requested `target_runtime_s` (within ±0.5s).
- **Provide Two Endings:** Generate two CTA options: (A) a direct, hard CTA and (B) a soft, looping CTA that transitions back to the beginning ('loop_back_to_scene_1').
- **OUTPUT JSON ONLY.** No markdown. No commentary.
""").strip()


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
        {"role": "user", "content": dedent(f"Analyze the reference short-form video and produce a director-ready breakdown.\nInputs (JSON):\n{evidence_json}\n\n{ANALYZER_USER_INSTRUCTIONS}").strip()}
    ]
    return messages


def build_script_generator_messages(
    *,
    analyzer_json: str,
    product_facts: dict,
    brand_voice: dict | None = None,
    target_runtime_s: int = 20,
    platform: str = "tiktok",
    cta_variants: list[str] | None = None
):
    if cta_variants is None:
        cta_variants = ["Check out our TikTok Shop. They're on sale right now.", "Tap to see options and pricing."]
    inputs_packet = {
        "platform": platform,
        "target_runtime_s": target_runtime_s,
        "analyzer_json": analyzer_json,
        "product_facts": product_facts,
        "brand_voice": brand_voice or {},
        "cta_variants": cta_variants
    }
    inputs_json = json.dumps(inputs_packet, ensure_ascii=False)
    user_msg = dedent(f"Create a new short-form video plan for the TARGET brand/product using the Analyzer JSON.\nInputs (JSON):\n{inputs_json}\n\n{SCRIPT_USER_INSTRUCTIONS_TEMPLATE}").strip()
    messages = [
        {"role": "system", "content": SCRIPT_SYSTEM_PREAMBLE},
        {"role": "user", "content": user_msg}
    ]
    return messages


def build_product_research_messages(
    brand: str, product: str, page_text: Optional[str] = None
):
    parts = [dedent(f'Research factual, legally compliant marketing claims for the product "{product}" from brand "{brand}".').strip()]
    if page_text:
        parts.append("Product page text:\n" + page_text.strip())
    parts.append(dedent("""
        Return JSON with exactly these fields:
        - "approved_claims": list of short, substantiated marketing claims
        - "required_disclaimers": list of disclaimers required for those claims
        - "forbidden": list of risky or prohibited claims to avoid

        If unsure or no data, use empty lists. Output JSON only with no commentary or extra keys.
    """).strip())
    user_content = "\n\n".join(parts)
    messages = [
        {"role": "system", "content": "You are a compliance-focused marketing assistant. Respond with JSON only."},
        {"role": "user", "content": user_content},
    ]
    return messages


def validate_analyzer_json(parsed: dict) -> list[str]:
    errs = []
    if "scenes" not in parsed or not isinstance(parsed["scenes"], list) or not parsed["scenes"]:
        errs.append("Analyzer JSON missing non-empty 'scenes'.")
    if "video_metadata" not in parsed:
        errs.append("Analyzer JSON missing 'video_metadata'.")
    else:
        vm = parsed["video_metadata"]
        if "duration_s" not in vm or not isinstance(vm["duration_s"], (int, float)):
            errs.append("'video_metadata.duration_s' missing or not numeric.")
    try:
        duration = float(parsed["video_metadata"]["duration_s"])
        last_end = float(parsed["scenes"][-1]["end_s"])
        if abs(last_end - duration) > 0.5: # Increased tolerance slightly
            errs.append(f"Last scene end_s ({last_end}) != duration_s ({duration}).")
    except Exception:
        pass
    return errs


def validate_script_json(parsed: dict, target_runtime_s: float | None = None) -> list[str]:
    errs = []
    try:
        if "script" not in parsed:
            errs.append("Script JSON missing 'script'.")
        else:
            scenes = parsed["script"].get("scenes", [])
            if not scenes:
                errs.append("'script.scenes' is empty.")
            elif scenes[0].get("start_s", 0) > 0.05:
                errs.append("First scene should start at ~0.0s.")
        if target_runtime_s is not None:
            got = float(parsed.get("target_runtime_s", 0))
            if abs(got - float(target_runtime_s)) > 1.0: # Increased tolerance
                errs.append(f"target_runtime_s mismatch: got {got}, expected ~{target_runtime_s}.")
    except Exception:
        pass
    return errs
