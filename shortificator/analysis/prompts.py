"""Prompt templates and content-mode guidance for the clip-selection LLM."""

CONTENT_MODE_GUIDANCE = {
    "talking-head": """CONTENT MODE: talking-head / face video.
- Prioritize crisp spoken insights, strong opinions, surprising explanations, useful examples, and self-contained stories.
- The transcript is the primary signal. Choose clips that make sense even when extracted from the long video.""",
    "gameplay": """CONTENT MODE: gameplay.
- Prioritize moments that sound like tension, combat, chase, surprise, failure, rare loot, betrayal, near death, victory, or a funny player reaction.
- Favor segments with emotional reactions, sudden changes, tactical decisions, or clear escalation.
- If the transcript is sparse, prefer windows around exclamations, short reactions, repeated urgency, or rapid context changes.""",
    "auto": """CONTENT MODE: auto.
- Infer whether the video is mainly spoken commentary or gameplay from the transcript.
- For commentary, use insight/story criteria. For gameplay, prefer tension, combat, surprise, failure, victory, and reactions.""",
}


ANALYSIS_PROMPT = """You are a video editor specialized in YouTube Shorts content.

Analyze the transcript below (with timestamps in seconds) and return ONLY valid JSON with the best clips for Shorts.

LANGUAGE REQUIREMENT (mandatory):
- Write "hook" and "reason" in {output_language}.
- NEVER use Chinese or any other language. Only {output_language}.

Selection criteria:
- Moments of insight or revelation
- Impactful lines that work without prior context
- Short, self-contained stories or examples
- Strong opening hooks (question, controversial claim, surprising fact)

{content_mode_guidance}

COUNT REQUIREMENT (mandatory):
- Return up to {candidate_pool_size} distinct candidates.
- If the transcript has enough usable material, return at least {desired_candidates} candidates.
- Do NOT stop after one good clip; keep searching for additional independent moments.
- Candidates must not all cover the same timestamp range.

TEMPORAL DIVERSITY REQUIREMENT (mandatory):
- Spread candidates across different parts of the transcript.
- Prefer non-overlapping timestamp ranges.
- Candidate start times should usually be at least {min_secs} seconds apart.
- Do not create multiple candidates from the same sentence or same local context.
- Use this time-window plan before repeating any local context:
{time_window_guidance}

HARD DURATION REQUIREMENT (mandatory):
- Each clip MUST last between {min_secs} and {max_secs} seconds: ({max_secs} >= end - start >= {min_secs}).
- If a strong moment is shorter than {min_secs}s, EXTEND start/end to include adjacent context until it reaches at least {min_secs}s.
- NEVER output a clip shorter than {min_secs}s or longer than {max_secs}s. Discard it instead.

Return ONLY this JSON, no explanations, no markdown:
{{
  "candidates": [
    {{
      "start": <float in seconds>,
      "end": <float in seconds>,
      "hook": "<impactful opening line, max 10 words>",
      "reason": "<why this clip works as a Short>",
      "score": <integer from 1 to 10, where 10 is best>
    }}
  ]
}}

TRANSCRIPT:
{transcript}

REMINDER: "hook" and "reason" MUST be written in {output_language}.
Do NOT use Chinese characters or any other language under any circumstance.
"""

# Sent as the system role to harden the language constraint: small multilingual
# models (e.g. qwen2.5) otherwise default to Chinese in the free-text fields.
ANALYSIS_SYSTEM_PROMPT = (
    "You are a video editor for YouTube Shorts. You ALWAYS write the 'hook' and "
    "'reason' fields strictly in {output_language}. You NEVER output Chinese "
    "characters (CJK) or any language other than {output_language}, no matter "
    "what language the transcript is in."
)
