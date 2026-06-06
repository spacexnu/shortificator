"""Burned-in subtitle rendering with PIL (UTF-8/accents) over OpenCV frames."""

import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..config import (
    SUBTITLE_BG_ALPHA,
    SUBTITLE_BG_COLOR,
    SUBTITLE_COLOR,
    SUBTITLE_FONT_CANDIDATES,
    SUBTITLE_FONT_PX,
)
from .style import DEFAULT_DYNAMIC_SUBTITLE_STYLE, DynamicSubtitleStyle


def resolve_subtitle_font_path() -> str | None:
    override = os.environ.get("SUBTITLE_FONT_PATH")
    if override and os.path.exists(override):
        return override
    for path in SUBTITLE_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# Cache the loaded fonts so we don't hit disk on every frame (keyed by path+size).
_SUBTITLE_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def get_subtitle_font(size_px: int = SUBTITLE_FONT_PX, font_path: str | None = None) -> ImageFont.FreeTypeFont:
    path = font_path or resolve_subtitle_font_path()
    if path is None:
        raise RuntimeError(
            "No TrueType font found for subtitles. Install one (e.g. "
            "fonts-dejavu) or set SUBTITLE_FONT_PATH to a .ttf file."
        )
    key = (path, size_px)
    if key not in _SUBTITLE_FONT_CACHE:
        _SUBTITLE_FONT_CACHE[key] = ImageFont.truetype(path, size_px)
    return _SUBTITLE_FONT_CACHE[key]


def draw_subtitle(frame: np.ndarray, text: str, frame_h: int, frame_w: int) -> np.ndarray:
    if not text.strip():
        return frame

    # Render with PIL so UTF-8 (accents/ç) draws correctly; cv2.putText + Hershey
    # only supports ASCII and turns accented chars into "?".
    font = get_subtitle_font()
    padding = 16

    # RGB image to draw on (OpenCV frames are BGR → convert both ways).
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top

    x = max(padding, (frame_w - tw) // 2)
    y = int(frame_h * 0.82)

    # Semi-transparent background box (blended via OpenCV before drawing text).
    box = (x - padding, y - padding, x + tw + padding, y + th + padding)
    overlay = frame.copy()
    cv2.rectangle(overlay, (box[0], box[1]), (box[2], box[3]), SUBTITLE_BG_COLOR, -1)
    cv2.addWeighted(overlay, SUBTITLE_BG_ALPHA, frame, 1 - SUBTITLE_BG_ALPHA, 0, frame)

    # Re-create the PIL canvas from the now-blended frame, then draw the text.
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    draw.text(
        (x - left, y - top),
        text,
        font=font,
        fill=SUBTITLE_COLOR,  # (R, G, B); white is symmetric so order is irrelevant
        stroke_width=2,
        stroke_fill=SUBTITLE_BG_COLOR,
    )

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _fit_dynamic_subtitle_lines(
    draw: ImageDraw.ImageDraw,
    words: list[str],
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> list[list[tuple[int, str]]]:
    lines: list[list[tuple[int, str]]] = []
    current_line: list[tuple[int, str]] = []
    current_width = 0
    space_width = int(draw.textlength(" ", font=font))

    for idx, word in enumerate(words):
        word_width = int(draw.textlength(word, font=font))
        next_width = word_width if not current_line else current_width + space_width + word_width
        if current_line and next_width > max_width and len(lines) < max_lines - 1:
            lines.append(current_line)
            current_line = [(idx, word)]
            current_width = word_width
        else:
            current_line.append((idx, word))
            current_width = next_width

    if current_line:
        lines.append(current_line)

    return lines[:max_lines]


def _dynamic_subtitle_word_font(
    style: DynamicSubtitleStyle,
    base_font_size: int,
    word_idx: int,
    active_word_idx: int | None,
) -> ImageFont.FreeTypeFont:
    if word_idx == active_word_idx:
        return get_subtitle_font(base_font_size + style.highlight_font_delta_px, style.font_path)
    return get_subtitle_font(base_font_size, style.font_path)


def _dynamic_subtitle_line_metrics(
    draw: ImageDraw.ImageDraw,
    line: list[tuple[int, str]],
    base_font_size: int,
    active_word_idx: int | None,
    space_width: int,
    style: DynamicSubtitleStyle,
) -> tuple[int, int]:
    width = 0
    height = 0
    for pos, (idx, word) in enumerate(line):
        font = _dynamic_subtitle_word_font(style, base_font_size, idx, active_word_idx)
        stroke_width = style.stroke_width + (style.highlight_stroke_extra if idx == active_word_idx else 0)
        left, top, right, bottom = draw.textbbox(
            (0, 0),
            word,
            font=font,
            stroke_width=stroke_width,
        )
        if pos:
            width += space_width
        width += right - left
        height = max(height, bottom - top)
    return width, height


# Text measurement is image-independent, so a shared 1x1 canvas is enough to size
# the lines/fonts. Layouts are cached because a word stays on screen for many
# consecutive frames, all sharing the same (words, highlight) layout.
_MEASURE_DRAW = ImageDraw.Draw(Image.new("RGB", (1, 1)))
_LAYOUT_CACHE: dict[tuple, tuple] = {}


def _compute_dynamic_layout(
    render_words: list[str],
    active_word_idx: int | None,
    frame_w: int,
    style: DynamicSubtitleStyle,
) -> tuple[list[list[tuple[int, str]]], list[int], list[int], int]:
    max_width = int(frame_w * style.max_width_ratio)
    lines: list[list[tuple[int, str]]] = []
    line_widths: list[int] = []
    line_heights: list[int] = []
    selected_font_size = style.font_px

    for font_size in range(style.font_px, style.min_font_px - 1, -style.font_step):
        font = get_subtitle_font(font_size, style.font_path)
        lines = _fit_dynamic_subtitle_lines(_MEASURE_DRAW, render_words, font, max_width, style.max_lines)
        line_widths = []
        line_heights = []
        space_width = int(_MEASURE_DRAW.textlength(" ", font=font))
        for line in lines:
            line_width, line_height = _dynamic_subtitle_line_metrics(
                _MEASURE_DRAW, line, font_size, active_word_idx, space_width, style
            )
            line_widths.append(line_width)
            line_heights.append(line_height)
        if line_widths and max(line_widths) <= max_width:
            selected_font_size = font_size
            break

    return lines, line_widths, line_heights, selected_font_size


def _get_dynamic_layout(
    render_words: list[str],
    active_word_idx: int | None,
    frame_w: int,
    style: DynamicSubtitleStyle,
):
    key = (
        tuple(render_words),
        active_word_idx,
        frame_w,
        style.font_px,
        style.min_font_px,
        style.font_step,
        style.max_lines,
        style.max_width_ratio,
        style.stroke_width,
        style.highlight_font_delta_px,
        style.highlight_stroke_extra,
        style.font_path,
    )
    layout = _LAYOUT_CACHE.get(key)
    if layout is None:
        layout = _compute_dynamic_layout(render_words, active_word_idx, frame_w, style)
        _LAYOUT_CACHE[key] = layout
    return layout


def draw_dynamic_subtitle(
    frame: np.ndarray,
    words: list[str],
    active_word_idx: int | None,
    frame_h: int,
    frame_w: int,
    style: DynamicSubtitleStyle = DEFAULT_DYNAMIC_SUBTITLE_STYLE,
) -> np.ndarray:
    if not words:
        return frame

    render_words = [word.upper() for word in words] if style.uppercase else list(words)
    lines, line_widths, line_heights, selected_font_size = _get_dynamic_layout(
        render_words, active_word_idx, frame_w, style
    )
    if not lines:
        return frame

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    line_gap = style.line_gap
    space_width = int(draw.textlength(" ", font=get_subtitle_font(selected_font_size, style.font_path)))
    shadow_dx, shadow_dy = style.shadow_offset

    block_h = sum(line_heights) + line_gap * (len(lines) - 1)
    y = int(frame_h * style.y_ratio - block_h / 2)

    for line, line_width, line_height in zip(lines, line_widths, line_heights, strict=False):
        x = (frame_w - line_width) // 2
        for idx, word in line:
            word_font = _dynamic_subtitle_word_font(style, selected_font_size, idx, active_word_idx)
            stroke_width = style.stroke_width
            fill = style.highlight_color if idx == active_word_idx else style.color
            if idx == active_word_idx:
                stroke_width += style.highlight_stroke_extra
            left, top, right, bottom = draw.textbbox(
                (0, 0),
                word,
                font=word_font,
                stroke_width=stroke_width,
            )
            word_w = right - left
            word_h = bottom - top
            word_y = y + (line_height - word_h) // 2
            text_x = x - left
            text_y = word_y - top
            draw.text(
                (text_x + shadow_dx, text_y + shadow_dy),
                word,
                font=word_font,
                fill=style.shadow_color,
                stroke_width=stroke_width,
                stroke_fill=style.shadow_color,
            )
            draw.text(
                (text_x, text_y),
                word,
                font=word_font,
                fill=fill,
                stroke_width=stroke_width,
                stroke_fill=style.stroke_color,
            )
            x += word_w + space_width
        y += line_height + line_gap

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
