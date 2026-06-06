"""Subtitle styling, word timing, and burned-in rendering."""

from .render import draw_dynamic_subtitle, draw_subtitle
from .style import DEFAULT_DYNAMIC_SUBTITLE_STYLE, DynamicSubtitleStyle, parse_color
from .timing import (
    get_subtitle_chunk_at_time,
    get_subtitle_words_at_time,
    get_words_at_time,
)

__all__ = [
    "DEFAULT_DYNAMIC_SUBTITLE_STYLE",
    "DynamicSubtitleStyle",
    "draw_dynamic_subtitle",
    "draw_subtitle",
    "get_subtitle_chunk_at_time",
    "get_subtitle_words_at_time",
    "get_words_at_time",
    "parse_color",
]
