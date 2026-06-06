"""Dynamic subtitle styling model and color parsing."""

from dataclasses import dataclass


@dataclass
class DynamicSubtitleStyle:
    """Configurable look of the ``--dynamic-subtitles`` style.

    Every field defaults to the current hardcoded behavior, so an empty
    ``DynamicSubtitleStyle()`` reproduces the previous output exactly.
    """

    # ``None`` falls back to resolve_subtitle_font_path() (env + candidates).
    font_path: str | None = None
    words_per_chunk: int = 4  # fixed group of words shown at once (static block)
    font_px: int = 78  # starting (largest) font size; auto-shrinks to fit width
    min_font_px: int = 48  # smallest size tried when shrinking to fit
    font_step: int = 4  # size decrement per shrink attempt
    max_lines: int = 2
    y_ratio: float = 0.74  # vertical center of the subtitle block (0=top, 1=bottom)
    max_width_ratio: float = 0.84  # subtitle block max width as a fraction of the frame
    line_gap: int = 10
    color: tuple[int, int, int] = (255, 255, 255)  # (R, G, B) for normal words
    highlight_color: tuple[int, int, int] = (255, 224, 64)  # current (karaoke) word
    stroke_color: tuple[int, int, int] = (0, 0, 0)
    shadow_color: tuple[int, int, int] = (0, 0, 0)
    shadow_offset: tuple[int, int] = (4, 5)
    stroke_width: int = 5
    highlight_font_delta_px: int = 4  # current word drawn slightly larger
    highlight_stroke_extra: int = 1  # current word drawn with thicker stroke
    uppercase: bool = True


DEFAULT_DYNAMIC_SUBTITLE_STYLE = DynamicSubtitleStyle()


def parse_color(value: str) -> tuple[int, int, int]:
    """Parse a color given as ``R,G,B`` or ``#RRGGBB`` into an (R, G, B) tuple."""
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
        if len(text) != 6:
            raise ValueError(f"Invalid hex color: {value!r} (expected #RRGGBB)")
        return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    parts = text.split(",")
    if len(parts) != 3:
        raise ValueError(f"Invalid color: {value!r} (expected R,G,B or #RRGGBB)")
    rgb = tuple(int(p) for p in parts)
    if any(c < 0 or c > 255 for c in rgb):
        raise ValueError(f"Color channels must be 0-255: {value!r}")
    return rgb  # type: ignore[return-value]
