"""Pure heuristics for shaping and pruning LLM-proposed clip candidates."""

from ..config import SHORT_MAX_SECS, SHORT_MIN_SECS
from ..models import Segment, ShortCandidate


def build_transcript_text(segments: list[Segment]) -> str:
    lines = []
    for seg in segments:
        ts = f"[{seg.start:.1f}s - {seg.end:.1f}s]"
        lines.append(f"{ts} {seg.text}")
    return "\n".join(lines)


def has_cjk(text: str) -> bool:
    """True if the string contains any CJK (Chinese/Japanese/Korean) character."""
    return any(
        "一" <= ch <= "鿿"  # CJK Unified Ideographs
        or "㐀" <= ch <= "䶿"  # CJK Extension A
        or "豈" <= ch <= "﫿"  # CJK Compatibility Ideographs
        for ch in text
    )


def overlap_ratio(a: ShortCandidate, b: ShortCandidate) -> float:
    overlap = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    shorter = max(0.01, min(a.end - a.start, b.end - b.start))
    return overlap / shorter


def dedupe_overlapping_candidates(
    candidates: list[ShortCandidate],
    max_candidates: int,
    max_overlap: float = 0.5,
) -> list[ShortCandidate]:
    selected = []
    for candidate in candidates:
        if all(overlap_ratio(candidate, existing) <= max_overlap for existing in selected):
            selected.append(candidate)
            if len(selected) >= max_candidates:
                break
    return selected


def plan_windows(video_end: float, count: int) -> list[tuple[float, float]]:
    """Split ``[0, video_end]`` into ``count`` consecutive, non-overlapping windows.

    Used to query the LLM per region so candidates are spread across the whole
    video instead of clustering. A single window is returned for degenerate inputs
    (one desired candidate or a non-positive duration).
    """
    count = max(1, count)
    video_end = max(0.0, video_end)
    if count == 1 or video_end == 0:
        return [(0.0, video_end)]
    size = video_end / count
    return [(i * size, video_end if i == count - 1 else (i + 1) * size) for i in range(count)]


def build_time_window_guidance(video_end: float, desired_candidates: int) -> str:
    if desired_candidates <= 1 or video_end <= 0:
        return "- Single candidate run: choose the strongest available moment."

    window_size = video_end / desired_candidates
    lines = []
    for i in range(desired_candidates):
        start = i * window_size
        end = video_end if i == desired_candidates - 1 else (i + 1) * window_size
        lines.append(f"- Candidate {i + 1}: prefer a strong moment starting between {start:.0f}s and {end:.0f}s.")
    return "\n".join(lines)


def fit_clip_window(
    start: float,
    end: float,
    video_end: float,
    min_secs: float = SHORT_MIN_SECS,
    max_secs: float = SHORT_MAX_SECS,
) -> tuple[float | None, float | None]:
    """Adjust an LLM-proposed clip to fit ``[min_secs, max_secs]``.

    Models often return clips shorter (or longer) than the allowed window despite
    the prompt. Instead of discarding them, expand/trim around the proposed center
    and clamp to the video bounds. Returns (None, None) if the video itself is
    shorter than ``min_secs``.
    """
    start = max(0.0, start)
    end = min(video_end, max(end, start))
    duration = end - start

    if video_end < min_secs:
        return None, None

    if duration < min_secs:
        # Grow around the center up to the minimum length.
        center = (start + end) / 2
        start = center - min_secs / 2
        end = center + min_secs / 2
    elif duration > max_secs:
        end = start + max_secs

    # Clamp to video bounds, preserving length where possible.
    if start < 0:
        end -= start
        start = 0.0
    if end > video_end:
        start -= end - video_end
        end = video_end
        start = max(0.0, start)

    return round(start, 2), round(end, 2)
