# prompts.py
# Updated prompts for multimodal analysis.

from textwrap import dedent
import json
from typing import Optional

# ... (ANALYZER_JSON_SCHEMA and SCRIPT_JSON_SCHEMA remain the same as the previous enhanced version) ...
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

# SCRIPT_JSON_SCHEMA, SCRIPT_SYSTEM_PREAMBLE, SCRIPT_USER_INSTRUCTIONS_TEMPLATE remain unchanged.
# Other helper functions like build_script_generator_messages, build_product_research_messages, validators also remain unchanged.


ANALYZER_SYSTEM_PREAMBLE = dedent("""
You are an expert Film Director and Viral Marketing Strategist. Your task is to perform a deep, multimodal analysis of the provided video file and break it down into a director-ready JSON structure.
Your analysis must identify the underlying formulas that make the video successful.
OUTPUT MUST BE VALID JSON ONLY that matches the provided schema exactly. Do not add comments or markdown.
""").strip()

ANALYZER_USER_INSTRUCTIONS_TEMPLATE = dedent(f"""
Return ONLY valid JSON adhering to this schema:

{ANALYZER_JSON_SCHEMA}

Key Analysis Tasks:
1)  **Deconstruct Core Logic:** Analyze the provided video file to identify its `video_category`, `narrative_structure`, and the `persuasion_tactics` it uses.
2)  **Profile the Persona:** From the video, thoroughly profile the creator's on-screen character in the `influencer_DNA.persona` object.
3)  **Detail the Filmmaking:** For each scene, provide granular detail on the `camera_movement`, `shot_composition`, and other visual and auditory elements present in the video.
4)  **Ensure Timing Accuracy:** The `video_metadata.duration_s` must be accurate, and the final scene's `end_s` must match it.
5)  **Identify Reusable Formulas:** In `transferable_patterns.must_keep`, distill the core, reusable formula for the video's success.
6)  **Output JSON Only.**
""").strip()

def build_analyzer_messages(duration_s: float, platform: str) -> str:
    """Builds the text prompt for the multimodal analyzer."""
    
    prompt = dedent(f"""
    Analyze the attached video file. The video's platform is {platform} and its exact duration is {duration_s} seconds.

    {ANALYZER_USER_INSTRUCTIONS_TEMPLATE}
    """).strip()
    
    return prompt

# ... (All other functions from the previous prompts.py file should be included here unchanged) ...
