"""Ollama-backed clip selection with structured (schema-constrained) output."""

import json
import re
import sys

from ..config import OUTPUT_LANGUAGE, SHORT_MAX_SECS, SHORT_MIN_SECS, ContentMode
from ..models import Segment, ShortCandidate
from .prompts import ANALYSIS_PROMPT, ANALYSIS_SYSTEM_PROMPT, CONTENT_MODE_GUIDANCE
from .selection import (
    build_transcript_text,
    dedupe_overlapping_candidates,
    fit_clip_window,
    has_cjk,
    plan_windows,
)

# Candidates requested per time window; the global dedup/top-N pass then trims the
# pooled results down to ``max_candidates``.
CANDIDATES_PER_WINDOW = 2


def build_analysis_schema(candidate_pool_size: int) -> dict:
    """JSON Schema passed to Ollama to enforce the output structure.

    Forcing the schema prevents small models from inventing their own JSON shape.
    """
    return {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "minItems": 1,
                "maxItems": max(1, candidate_pool_size),
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                        "hook": {"type": "string"},
                        "reason": {"type": "string"},
                        "score": {"type": "number"},
                    },
                    "required": ["start", "end", "hook", "reason", "score"],
                },
            }
        },
        "required": ["candidates"],
    }


def _request_window_candidates(
    ollama,
    model: str,
    segments: list[Segment],
    output_language: str,
    content_mode: ContentMode,
    min_secs: float,
    max_secs: float,
    video_end: float,
    pool_size: int,
    time_window_guidance: str,
) -> list[ShortCandidate]:
    """Run a single structured Ollama request and return its fitted candidates."""
    prompt = ANALYSIS_PROMPT.format(
        transcript=build_transcript_text(segments),
        min_secs=min_secs,
        max_secs=max_secs,
        output_language=output_language,
        desired_candidates=pool_size,
        candidate_pool_size=pool_size,
        time_window_guidance=time_window_guidance,
        content_mode_guidance=CONTENT_MODE_GUIDANCE[content_mode],
    )

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": ANALYSIS_SYSTEM_PROMPT.format(output_language=output_language),
                },
                {"role": "user", "content": prompt},
            ],
            format=build_analysis_schema(pool_size),
            options={"temperature": 0.2, "num_predict": 4096},
        )
    except Exception as e:
        print(
            f"[ERROR] Failed to call Ollama (model '{model}'). "
            f"Check that it is running on localhost:11434 and that the model was pulled.\n"
            f"        Detail: {e}"
        )
        return []

    raw = response["message"]["content"]

    # Extract JSON even if it comes wrapped in junk
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        print(f"[WARN] LLM did not return valid JSON. Response:\n{raw[:500]}")
        return []

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        print(f"[WARN] Malformed LLM JSON ({e}). Response:\n{raw[:500]}")
        return []

    candidates = []
    for c in data.get("candidates", []):
        start, end = fit_clip_window(float(c["start"]), float(c["end"]), video_end, min_secs, max_secs)
        if start is None:
            continue  # video too short to host even a minimal clip
        candidates.append(
            ShortCandidate(
                start=start,
                end=end,
                hook=c.get("hook", ""),
                reason=c.get("reason", ""),
                score=c.get("score", 5),
            )
        )
    return candidates


def analyze_with_llm(
    segments: list[Segment],
    model: str = "llama3",
    output_language: str = OUTPUT_LANGUAGE,
    max_candidates: int = 5,
    content_mode: ContentMode = "talking-head",
    min_secs: float = SHORT_MIN_SECS,
    max_secs: float = SHORT_MAX_SECS,
) -> list[ShortCandidate]:
    try:
        import ollama
    except ImportError:
        print("[ERROR] ollama not installed. Run: pip install ollama")
        sys.exit(1)

    print(f"\n[2/4] Analyzing best clips with Ollama ({model}, content={content_mode})...")
    if not segments:
        print("      0 valid candidates found.")
        return []

    video_end = segments[-1].end
    # Query one window per desired Short so candidates are spread across the whole
    # video instead of clustering wherever the model latched on first.
    windows = plan_windows(video_end, max_candidates)
    print(f"      Scanning {len(windows)} time window(s) across {video_end:.0f}s of video...")

    candidates: list[ShortCandidate] = []
    for index, (w_start, w_end) in enumerate(windows, start=1):
        subset = [s for s in segments if w_start <= s.start < w_end]
        if not subset:
            continue
        guidance = (
            f"- These timestamps belong to the {w_start:.0f}s-{w_end:.0f}s region of the video. "
            "Pick the strongest self-contained moment(s) within it."
        )
        window_candidates = _request_window_candidates(
            ollama,
            model,
            subset,
            output_language,
            content_mode,
            min_secs,
            max_secs,
            video_end,
            CANDIDATES_PER_WINDOW,
            guidance,
        )
        print(
            f"      Window {index}/{len(windows)} ({w_start:.0f}-{w_end:.0f}s): {len(window_candidates)} candidate(s)"
        )
        candidates.extend(window_candidates)

    candidates.sort(key=lambda x: x.score, reverse=True)
    deduped_candidates = dedupe_overlapping_candidates(candidates, max_candidates)

    removed_count = len(candidates) - len(deduped_candidates)
    if removed_count:
        print(f"      Removed {removed_count} overlapping duplicate candidate(s).")
    if len(deduped_candidates) < min(max_candidates, len(candidates)):
        print(
            f"[WARN] Only {len(deduped_candidates)} non-overlapping candidate(s) found. "
            "Try a larger/different model or rerun the analysis."
        )
    candidates = deduped_candidates

    # Safety net: some multilingual models (notably qwen2.5) ignore the language
    # instruction and emit Chinese (CJK) in the free-text fields. Make it loud.
    if any(has_cjk(c.hook) or has_cjk(c.reason) for c in candidates):
        print(
            f"[WARN] Model '{model}' returned Chinese (CJK) text despite the "
            f"language requirement ({output_language}). Try a less Chinese-biased "
            f"model, e.g. --model mistral-small or --model llama3.1:8b."
        )

    print(f"      {len(candidates)} valid candidates found.")
    for i, c in enumerate(candidates):
        print(f"      [{i + 1}] {c.start:.1f}s-{c.end:.1f}s (score={c.score}) — {c.hook}")

    return candidates
