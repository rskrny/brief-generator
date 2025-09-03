# prompts.py
# Updated prompts for multimodal analysis.

from textwrap import dedent
import json
from typing import Optional, List, Dict

# --- ANALYZER SCHEMA ---
ANALYZER_JSON_SCHEMA = dedent("""
{
  "video_metadata": { "platform": "tiktok|reels|ytshorts", "duration_s": 0, "aspect_ratio": "9:16" },
  "global_style": {
    "video_category": "Unboxing|Tutorial|Skit|Challenge|Testimonial|Product-Demo|Day-in-the-Life",
    "narrative_structure": "Problem/Agitate/Solve|Before-and-After|Direct-Comparison|Myth-Busting|Storytelling-Hook",
    "hook_type": ["pattern_interrupt", "reply_to_comment", "question_hook"],
    "promise": "A clear statement of what the viewer will gain or learn.",
    "payoff": "The fulfillment of the promise.",
    "cta_core": "The primary call to action.",
    "persuasion_tactics": ["Social-Proof", "Scarcity", "Authority", "Demonstration", "Urgency"],
    "music": {"genre":"", "bpm": 0, "mood":[]}
  },
  "influencer_DNA": {
    "persona": {
      "archetype": "The-Expert|The-Relatable-Friend|The-Entertainer|The-Aspirational-Figure",
      "communication_style": "Direct-and-Informative|Storytelling|Humorous|Energetic"
    }
  },
  "scenes": [
    {
      "idx": 1, "start_s": 0.0, "end_s": 0.0,
      "shot_type": "CU|MCU|MS|WS", "camera_movement": "Static|Handheld|Pan|Tilt",
      "action": "", "dialogue_vo": "", "on_screen_text": []
    }
  ],
  "transferable_patterns": { "must_keep": [], "rewrite": [] }
}
""").strip()

# --- SCRIPT SCHEMA ---
SCRIPT_JSON_SCHEMA = dedent("""
{
  "target_runtime_s": 0,
  "script": {
    "scenes": [
      {
        "idx": 1, "start_s": 0.0, "end_s": 0.0,
        "shot_type": "CU|MCU|MS|WS", "camera_movement": "Static|Handheld|Pan|Tilt",
        "action": "", "dialogue_vo": "", "on_screen_text": []
      }
    ],
    "cta_options": [
      {"variant":"A", "dialogue":""},
      {"variant":"B", "dialogue":""}
    ]
  }
}
""").strip()

# --- ANALYZER PROMPT BUILDER ---
ANALYZER_PROMPT_TEMPLATE = dedent(f"""
You are an expert Film Director and Viral Marketing Strategist. Analyze the provided video file and break it down into a director-ready JSON structure.
Your analysis must be deep, identifying the underlying formulas that make the video successful.
The video's platform is {{platform}} and its exact duration is {{duration_s}} seconds.

OUTPUT MUST BE VALID JSON ONLY that matches this schema exactly:
{ANALYZER_JSON_SCHEMA}
""").strip()

def build_analyzer_messages(duration_s: float, platform: str) -> str:
    """Builds the text prompt for the multimodal analyzer."""
    return ANALYZER_PROMPT_TEMPLATE.format(duration_s=duration_s, platform=platform)

# --- SCRIPT GENERATOR PROMPT BUILDER ---
SCRIPT_PROMPT_TEMPLATE = dedent(f"""
You are a Creative Director specializing in high-performing video ads.
Use the provided Analyzer JSON of a successful reference video to create a NEW script for a different product.
The goal is to replicate the *formula* of the reference video (its structure, persona, and tactics) for the new product.

**ANALYZER JSON (Reference Video Breakdown):**
{{analyzer_json}}

**TARGET PRODUCT FACTS:**
{{product_facts}}

**CONSTRAINTS:**
- Adopt the `narrative_structure`, `video_category`, and `influencer_DNA.persona` from the analysis.
- All product claims in dialogue or on-screen text MUST come from the `approved_claims` whitelist.
- The total runtime must be exactly {{target_runtime_s}} seconds.
- Provide two CTA options: a direct CTA and a soft, looping CTA.

OUTPUT MUST BE VALID JSON ONLY that matches this schema exactly:
{SCRIPT_JSON_SCHEMA}
""").strip()

def build_script_generator_messages(analyzer_json: str, product_facts: dict, target_runtime_s: int, platform: str, **kwargs) -> List[Dict[str, str]]:
    """Builds the messages list for the script generator."""
    content = SCRIPT_PROMPT_TEMPLATE.format(
        analyzer_json=analyzer_json,
        product_facts=json.dumps(product_facts),
        target_runtime_s=target_runtime_s
    )
    return [{"role": "user", "content": content}]

# --- PRODUCT RESEARCH PROMPT BUILDER ---
def build_product_research_messages(brand: str, product: str, page_text: Optional[str] = None) -> List[Dict[str, str]]:
    """Builds the messages for the product research task."""
    parts = [f'Research factual, legally compliant marketing claims for the product "{product}" from brand "{brand}".']
    if page_text:
        parts.append("Product page text:\n" + page_text.strip())
    parts.append(dedent("""
        Return JSON with exactly these fields:
        - "approved_claims": list of short, substantiated marketing claims
        - "required_disclaimers": list of disclaimers required for those claims
        - "forbidden": list of risky or prohibited claims to avoid
        If unsure, use empty lists. Output JSON only.
    """).strip())
    
    return [
        {"role": "system", "content": "You are a compliance-focused marketing assistant. Respond with JSON only."},
        {"role": "user", "content": "\n\n".join(parts)},
    ]

# --- VALIDATORS ---
def validate_analyzer_json(parsed: dict) -> list[str]:
    """Lightweight checks for the generated analyzer JSON."""
    errs = []
    if "scenes" not in parsed or not parsed.get("scenes"):
        errs.append("Analyzer JSON missing 'scenes'.")
    if "video_metadata" not in parsed:
        errs.append("Analyzer JSON missing 'video_metadata'.")
    else:
        duration = parsed["video_metadata"].get("duration_s", 0)
        if not isinstance(duration, (int, float)) or duration == 0:
            errs.append("'video_metadata.duration_s' is invalid.")
        try:
            last_end = parsed["scenes"][-1].get("end_s", 0)
            if abs(last_end - duration) > 1.0: # Allow 1s tolerance
                errs.append(f"Last scene end_s ({last_end}) does not match video duration ({duration}).")
        except (IndexError, KeyError):
            pass # Handled by the 'missing scenes' check
    return errs

def validate_script_json(parsed: dict, target_runtime_s: float | None) -> list[str]:
    """Lightweight checks for the generated script JSON."""
    errs = []
    if "script" not in parsed or "scenes" not in parsed.get("script", {}) or not parsed["script"]["scenes"]:
        errs.append("Script JSON is missing 'scenes'.")
    if target_runtime_s is not None:
        got = parsed.get("target_runtime_s", 0)
        if abs(got - target_runtime_s) > 1.5: # Allow 1.5s tolerance
            errs.append(f"Script's target_runtime_s ({got}) differs from the expected ({target_runtime_s:.2f}).")
    return errs
