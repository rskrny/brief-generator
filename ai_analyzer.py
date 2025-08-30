# ai_analyzer.py
# Utilities for prepping evidence for the Analyzer:
# - Parse SRT/VTT captions to time-aligned segments and plain text
# - Validate/normalize OCR keyframes JSON
# - Lightweight helpers for duration hints, etc.
#
# NOTE: No LLM prompts here. All prompting is handled in app.py via prompts.py.

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import re
import json


# =============================
# Data structures
# =============================

@dataclass
class CaptionSegment:
    start_s: float
    end_s: float
    text: str


# =============================
# SRT/VTT parsing
# =============================

_TS_RE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})(?P<ms>[.,]\d{1,3})?"
)

def _ts_to_seconds(ts: str) -> float:
    """
    Convert timestamp like '00:00:03,500' or '0:00:03.5' to seconds.
    """
    ts = ts.strip()
    m = _TS_RE.search(ts)
    if not m:
        return 0.0
    h = int(m.group("h"))
    m_ = int(m.group("m"))
    s = int(m.group("s"))
    ms = m.group("ms")
    frac = 0.0
    if ms:
        ms = ms.replace(",", ".")
        try:
            frac = float(ms)
        except Exception:
            frac = 0.0
    return h * 3600 + m_ * 60 + s + frac


def srt_to_segments(srt_text: str) -> List[CaptionSegment]:
    """
    Parse SRT/VTT-ish text into a list of CaptionSegment.
    Robust to minor format issues.
    """
    if not srt_text:
        return []

    # Normalize newlines
    text = srt_text.replace("\r\n", "\n").replace("\r", "\n")
    # Split on blank lines; SRT blocks are typically separated by blank lines
    blocks = re.split(r"\n\s*\n", text.strip())

    segments: List[CaptionSegment] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue

        # Many SRTs have an index line we can ignore (e.g., "42")
        # Find the timestamp line among the first two lines.
        ts_line_idx = None
        for i in range(min(2, len(lines))):
            if "-->" in lines[i]:
                ts_line_idx = i
                break

        if ts_line_idx is None:
            # Try to find a timestamp line anywhere in the block
            for i, ln in enumerate(lines):
                if "-->" in ln:
                    ts_line_idx = i
                    break

        if ts_line_idx is None:
            # Not an SRT block; skip
            continue

        ts_line = lines[ts_line_idx]
        content_lines = lines[ts_line_idx + 1 :]
        # Parse timestamp line
        parts = [p.strip() for p in ts_line.split("-->")]
        if len(parts) != 2:
            continue
        start_s = _ts_to_seconds(parts[0])
        end_s = _ts_to_seconds(parts[1])

        # Join remaining lines as text; strip speaker tags like [Music], (Applause), etc.
        content = " ".join(content_lines)
        content = re.sub(r"\[(?:[^\]]+)\]|\((?:[^)]+)\)", "", content).strip()

        if content:
            segments.append(CaptionSegment(start_s=start_s, end_s=end_s, text=content))

    # Deduplicate or merge near-duplicates if needed
    merged: List[CaptionSegment] = []
    for seg in segments:
        if merged and abs(seg.start_s - merged[-1].start_s) < 0.01 and seg.text == merged[-1].text:
            # Extend the end time if it's essentially the same caption continued
            merged[-1].end_s = max(merged[-1].end_s, seg.end_s)
        else:
            merged.append(seg)

    return merged


def srt_to_plaintext(srt_text: str) -> str:
    """
    Convert SRT/VTT into a single de-duplicated plain text transcript.
    """
    segs = srt_to_segments(srt_text)
    # Coalesce repeated lines that happen due to captions splitting
    chunks: List[str] = []
    last = ""
    for s in segs:
        t = s.text.strip()
        if t and t != last:
            chunks.append(t)
            last = t
    return " ".join(chunks).strip()


# =============================
# OCR keyframes helpers
# =============================

def normalize_ocr_keyframes(ocr_json_str: Optional[str]) -> str:
    """
    Accepts a JSON string describing OCR per keyframe, returns a normalized JSON string.

    Expected shape (flexible):
      {"frames":[
          {"t":0.0, "text":["Replying to @...","SALE 20% OFF"]},
          {"t":1.5, "text":["Tap to learn more"]}
      ]}

    If input is None or invalid, returns {"frames": []}.
    """
    if not ocr_json_str:
        return json.dumps({"frames": []})

    try:
        data = json.loads(ocr_json_str)
    except Exception:
        return json.dumps({"frames": []})

    frames = data.get("frames", [])
    norm_frames: List[Dict[str, Any]] = []
    for fr in frames:
        try:
            t = float(fr.get("t", 0.0))
        except Exception:
            t = 0.0
        txt = fr.get("text", [])
        if isinstance(txt, str):
            txt = [txt]
        if not isinstance(txt, list):
            txt = []
        # Clean individual items
        clean_txt = []
        for item in txt:
            if not isinstance(item, str):
                continue
            val = item.strip()
            if val:
                clean_txt.append(val)
        norm_frames.append({"t": t, "text": clean_txt})

    norm_frames.sort(key=lambda x: x["t"])
    return json.dumps({"frames": norm_frames}, ensure_ascii=False)


def validate_ocr_json(ocr_json_str: str) -> Tuple[bool, List[str]]:
    """
    Validate normalized OCR JSON for obvious issues.
    Returns (ok, errors).
    """
    errs: List[str] = []
    try:
        data = json.loads(ocr_json_str or "{}")
    except Exception:
        return False, ["Invalid JSON"]

    frames = data.get("frames")
    if frames is None or not isinstance(frames, list):
        errs.append("Missing 'frames' array.")
        return False, errs

    for i, fr in enumerate(frames):
        if "t" not in fr or not isinstance(fr["t"], (int, float)):
            errs.append(f"frames[{i}].t missing or not numeric")
        if "text" not in fr or not isinstance(fr["text"], list):
            errs.append(f"frames[{i}].text missing or not a list")
        else:
            for j, item in enumerate(fr["text"]):
                if not isinstance(item, str):
                    errs.append(f"frames[{i}].text[{j}] not a string")

    return (len(errs) == 0), errs


# =============================
# Duration helpers
# =============================

def duration_hint_from_segments(segments: List[CaptionSegment]) -> Optional[float]:
    """
    If no explicit duration is provided, try to infer a rough duration from the last caption end.
    """
    if not segments:
        return None
    try:
        return max(seg.end_s for seg in segments if isinstance(seg.end_s, (int, float)))
    except Exception:
        return None


# =============================
# Pretty formatters (for logs/UI)
# =============================

def segments_to_debug_table(segments: List[CaptionSegment]) -> List[Dict[str, Any]]:
    """
    Turns segments into a list of dicts for displaying in Streamlit tables or logs.
    """
    out: List[Dict[str, Any]] = []
    for s in segments:
        out.append({"start_s": round(s.start_s, 3), "end_s": round(s.end_s, 3), "text": s.text})
    return out


# =============================
# Module self-test (optional)
# =============================

if __name__ == "__main__":
    demo_srt = """1
00:00:00,000 --> 00:00:02,400
Replying to @jamal39713

2
00:00:02,400 --> 00:00:04,800
Crystal-clear calls, anywhere.

3
00:00:04,800 --> 00:00:07,500
Tap to see options and pricing.
"""
    segs = srt_to_segments(demo_srt)
    print("Segments:", segments_to_debug_table(segs))
    print("Plain:", srt_to_plaintext(demo_srt))

    ocr = {"frames":[{"t":0.0,"text":["Replying to @..."]},{"t":1.6,"text":"Crystal-clear calls, anywhere."}]}
    norm = normalize_ocr_keyframes(json.dumps(ocr))
    print("OCR normalized:", norm)
    print("OCR valid:", validate_ocr_json(norm))
