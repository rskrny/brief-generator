# prompts.py
from typing import Dict, Any, List, Optional

# ==================================
# ===== 1. ANALYZER (MULTIMODAL) =====
# ==================================

def build_analyzer_messages(duration_s: float, platform: str) -> str:
    """Builds the single prompt string for the multimodal video analyzer."""
    return f"""
You are an expert creative director specializing in short-form video ads for {platform}.
Analyze the provided video file, which is {duration_s:.2f} seconds long.
Your analysis must be deep and insightful, covering the following areas.
Respond ONLY with a valid JSON object following this schema:

{{
  "objective": "A concise, one-sentence summary of the video's primary goal (e.g., 'Drive purchases of X product by showcasing its core benefit Y').",
  "target_audience": "A brief description of the most likely target audience for this ad.",
  "key_message": "The single most important takeaway message the ad wants to leave with the viewer.",
  "hook_strategy": {{
    "type": "Categorize the hook (e.g., 'Problem/Solution', 'Surprising Statement', 'Question', 'Visual Gag', 'Testimonial').",
    "description": "Explain exactly what happens in the first 3 seconds and why it's effective at capturing attention."
  }},
  "pacing_and_editing": {{
    "type": "Describe the editing style (e.g., 'Fast-paced with quick cuts', 'Slow and cinematic', 'UGC-style with minimal cuts').",
    "description": "Explain how the pacing and editing choices contribute to the ad's overall feel and effectiveness."
  }},
  "tone_and_vibe": "Describe the overall mood and personality of the ad (e.g., 'Humorous and relatable', 'Aspirational and luxurious', 'Informative and trustworthy').",
  "call_to_action": {{
    "type": "Categorize the CTA (e.g., 'Direct Command', 'Benefit-driven', 'Urgency-based', 'Soft encouragement').",
    "description": "Describe the specific call to action used in the ad (verbally, visually, or text overlay)."
  }}
}}
"""

# ================================
# ===== 2. PRODUCT RESEARCH ======
# ================================

def build_product_research_messages(brand: str, product: str, page_text: Optional[str] = None) -> List[Dict[str, Any]]:
    """Builds the messages list for the product fact researcher."""
    system_prompt = """
You are a meticulous, risk-averse marketing compliance assistant.
Your task is to analyze product information and generate a list of approved marketing claims, forbidden claims, and required disclaimers.
- APPROVED claims must be directly supported by the provided text. Do not invent or infer claims.
- FORBIDDEN claims are boilerplate legal warnings against making unsubstantiated statements.
- REQUIRED disclaimers are standard legal notices.

Respond ONLY with a valid JSON object matching this schema:
{{
  "approved_claims": ["List of verifiable claims, e.g., 'Made with 100% organic cotton.'"],
  "forbidden": ["List of claims to avoid, e.g., 'medical/health claims without substantiation'"],
  "required_disclaimers": ["List of necessary legal disclaimers, e.g., 'Results may vary.'"]
}}
"""
    
    user_prompt = f"Brand: {brand}\nProduct: {product}\n"
    if page_text:
        user_prompt += f"Product Page Text:\n---\n{page_text}\n---"
    else:
        user_prompt += "No product page text provided. Base your analysis on the product name alone."

    # CORRECTED FORMAT: Use 'parts' key instead of 'content'
    return [
        {'role': 'user', 'parts': [{'text': system_prompt}]},
        {'role': 'model', 'parts': [{'text': '{"approved_claims": [], "forbidden": [], "required_disclaimers": []}'}]},
        {'role': 'user', 'parts': [{'text': user_prompt}]}
    ]


# ================================
# ===== 3. SCRIPT GENERATOR ======
# ================================

def build_script_generator_messages(analyzer_json: str, product_facts: Dict[str, Any], target_runtime_s: int, platform: str) -> List[Dict[str, Any]]:
    """Builds the messages list for the script generator."""

    system_prompt = f"""
You are an expert scriptwriter for high-performance short-form video ads on {platform}.
You will be given a deep analysis of a successful reference video and a set of facts about a new product.
Your task is to create a new, original script for the new product that ADAPTS the successful formula of the reference video.
Do NOT simply copy the reference video. Adapt its structure, pacing, and tone to the new product.
The total duration of all scenes must closely match the target runtime of {target_runtime_s} seconds.

Adhere to all constraints provided in the product facts, especially the forbidden claims and required disclaimers.
Respond ONLY with a valid JSON object that follows this schema:

{{
  "title": "A short, catchy title for the new ad.",
  "logline": "A one-sentence summary of the ad's concept.",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_s": "The duration of this specific scene in seconds (integer).",
      "visuals_description": "A detailed description of what the viewer sees. Be specific about shots, angles, and on-screen text.",
      "audio_description": "The corresponding voiceover, dialogue, or key sound effects for this scene."
    }}
  ]
}}
"""

    user_prompt = (
        f"Reference Video Analysis:\n---\n{analyzer_json}\n---\n\n"
        f"New Product Facts:\n---\n{product_facts}\n---"
    )

    # CORRECTED FORMAT: Use 'parts' key instead of 'content'
    return [
        {'role': 'user', 'parts': [{'text': system_prompt}]},
        {'role': 'model', 'parts': [{'text': '{"title": "", "logline": "", "scenes": []}'}]},
        {'role': 'user', 'parts': [{'text': user_prompt}]}
    ]


# ================================
# ===== 4. JSON VALIDATORS ======
# ================================

def validate_analyzer_json(data: Dict[str, Any]) -> List[str]:
    """Validates the structure of the analyzer's JSON output."""
    errors = []
    required_keys = ["objective", "target_audience", "key_message", "hook_strategy", "pacing_and_editing", "tone_and_vibe", "call_to_action"]
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: '{key}'")
    
    if "hook_strategy" in data and not isinstance(data["hook_strategy"], dict):
        errors.append("'hook_strategy' must be a dictionary.")
    
    return errors

def validate_script_json(data: Dict[str, Any], target_runtime_s: int) -> List[str]:
    """Validates the script JSON and checks runtime."""
    warnings = []
    if "scenes" not in data or not isinstance(data["scenes"], list):
        warnings.append("Missing 'scenes' list.")
        return warnings

    total_duration = 0
    for i, scene in enumerate(data["scenes"]):
        if not isinstance(scene, dict):
            warnings.append(f"Scene {i+1} is not a valid dictionary.")
            continue
        
        duration = scene.get("duration_s")
        if isinstance(duration, int):
            total_duration += duration
        else:
            warnings.append(f"Scene {i+1} has an invalid or missing 'duration_s'.")

    duration_diff = abs(total_duration - target_runtime_s)
    if duration_diff > 3:
        warnings.append(f"Total script duration ({total_duration}s) is more than 3s different from target ({target_runtime_s}s).")
        
    return warnings
