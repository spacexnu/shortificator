"""Build SubRip (.srt) subtitle files from transcript segments."""

from ..models import Segment


def format_timestamp(seconds: float) -> str:
    """Format ``seconds`` as an SRT timestamp (``HH:MM:SS,mmm``)."""
    total_ms = max(0, round(seconds * 1000))
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(segments: list[Segment], start: float = 0.0, end: float | None = None) -> str:
    """Render the segments overlapping ``[start, end]`` as SRT text.

    Cue timestamps are clamped to the window and shifted so the clip starts at
    zero, matching a Short rendered from the same range. ``end=None`` keeps every
    segment from ``start`` onward.
    """
    cues = []
    for seg in segments:
        if seg.end <= start or (end is not None and seg.start >= end):
            continue
        text = seg.text.strip()
        if not text:
            continue
        cue_start = max(seg.start, start) - start
        cue_end = (seg.end if end is None else min(seg.end, end)) - start
        if cue_end <= cue_start:
            continue
        cues.append((cue_start, cue_end, text))

    blocks = []
    for index, (cue_start, cue_end, text) in enumerate(cues, start=1):
        blocks.append(f"{index}\n{format_timestamp(cue_start)} --> {format_timestamp(cue_end)}\n{text}\n")
    return "\n".join(blocks)
