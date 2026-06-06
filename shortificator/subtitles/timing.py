"""Map a playback timestamp to the words that should be on screen."""

from ..config import WORDS_PER_SUBTITLE_CHUNK
from ..models import Segment


def get_words_at_time(segments: list[Segment], t: float) -> str:
    """Return the words active at time t as a subtitle string."""
    words, _ = get_subtitle_words_at_time(segments, t)
    return " ".join(words)


def get_subtitle_words_at_time(segments: list[Segment], t: float) -> tuple[list[str], int | None]:
    """Return the active subtitle word chunk and the current word index."""
    for seg in segments:
        if seg.start <= t <= seg.end:
            if seg.words:
                current_idx = None
                for idx, word in enumerate(seg.words):
                    if word["start"] <= t <= word["end"] + 0.3:
                        current_idx = idx
                        break
                if current_idx is not None:
                    half_window = WORDS_PER_SUBTITLE_CHUNK // 2
                    chunk_start = max(0, current_idx - half_window)
                    chunk_end = min(len(seg.words), chunk_start + WORDS_PER_SUBTITLE_CHUNK)
                    chunk_start = max(0, chunk_end - WORDS_PER_SUBTITLE_CHUNK)
                    words = [w["word"].strip() for w in seg.words[chunk_start:chunk_end]]
                    return words, current_idx - chunk_start
            return seg.text[:60].split(), None
    return [], None


def get_subtitle_chunk_at_time(segments: list[Segment], t: float, chunk_size: int) -> tuple[list[str], int | None]:
    """Return a *fixed* group of words for time ``t`` and the highlighted index.

    Unlike the sliding window of ``get_subtitle_words_at_time``, the words are
    partitioned into static blocks of ``chunk_size``. The block only changes when
    speech crosses into the next group, so the text stays put while the highlight
    moves across it. During micro-pauses (and short gaps between segments) the
    last block is held instead of blanking out, to avoid flicker.
    """
    chunk_size = max(1, chunk_size)

    # Active segment if t is inside one; otherwise the most recent one that has
    # already started (so its last block is held during the gap that follows).
    active_seg: Segment | None = None
    for seg in segments:
        if seg.start <= t <= seg.end:
            active_seg = seg
            break
        if seg.start <= t:
            active_seg = seg
        else:
            break

    if active_seg is None:
        return [], None
    if not active_seg.words:
        return active_seg.text[:60].split(), None

    words = active_seg.words
    current_idx: int | None = None
    for idx, word in enumerate(words):
        if word["start"] <= t <= word["end"] + 0.3:
            current_idx = idx
            break

    if current_idx is None:
        # Micro-pause/gap: hold the latest block whose first word already started.
        chunk_index = 0
        for ci in range(0, len(words), chunk_size):
            if words[ci]["start"] <= t:
                chunk_index = ci // chunk_size
            else:
                break
        active_in_chunk = None
    else:
        chunk_index = current_idx // chunk_size
        active_in_chunk = current_idx - chunk_index * chunk_size

    start = chunk_index * chunk_size
    block = [w["word"].strip() for w in words[start : start + chunk_size]]
    return block, active_in_chunk
