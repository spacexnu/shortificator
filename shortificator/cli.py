"""Command-line interface for the shortificator pipeline."""

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_OUTPUT_FPS, OUTPUT_LANGUAGE, SHORT_MAX_SECS, SHORT_MIN_SECS
from .subtitles.style import DEFAULT_DYNAMIC_SUBTITLE_STYLE, DynamicSubtitleStyle, parse_color


def build_dynamic_subtitle_style(args) -> DynamicSubtitleStyle:
    """Build a DynamicSubtitleStyle from CLI args, keeping defaults for omitted ones."""
    style = DynamicSubtitleStyle()
    if args.sub_font:
        if not Path(args.sub_font).exists():
            print(f"[ERROR] Subtitle font not found: {args.sub_font}")
            sys.exit(1)
        style.font_path = args.sub_font
    if args.sub_font_size:
        style.font_px = args.sub_font_size
        style.min_font_px = min(style.min_font_px, args.sub_font_size)
    if args.sub_stroke_width is not None:
        style.stroke_width = args.sub_stroke_width
    if args.sub_y_ratio is not None:
        style.y_ratio = args.sub_y_ratio
    if args.sub_max_lines:
        style.max_lines = args.sub_max_lines
    if args.sub_words_per_chunk:
        if args.sub_words_per_chunk < 1:
            print("[ERROR] --sub-words-per-chunk must be >= 1.")
            sys.exit(1)
        style.words_per_chunk = args.sub_words_per_chunk
    if args.sub_no_uppercase:
        style.uppercase = False
    try:
        if args.sub_color:
            style.color = parse_color(args.sub_color)
        if args.sub_highlight_color:
            style.highlight_color = parse_color(args.sub_highlight_color)
        if args.sub_stroke_color:
            style.stroke_color = parse_color(args.sub_stroke_color)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    return style


def parse_timestamp(value: str) -> float:
    """Parse 'SS', 'MM:SS' or 'HH:MM:SS' (fractions allowed) into seconds."""
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"Invalid timestamp: '{value}'")
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid timestamp: '{value}'") from None
    if any(n < 0 for n in numbers):
        raise ValueError(f"Invalid timestamp: '{value}'")
    seconds = 0.0
    for n in numbers:
        seconds = seconds * 60 + n
    return seconds


def parse_clips(specs: list[str]) -> list[tuple[float, float]]:
    """Parse repeated --clip START-END specs into (start, end) pairs in seconds."""
    clips = []
    for spec in specs:
        start_str, sep, end_str = spec.partition("-")
        if not sep or not start_str or not end_str:
            raise ValueError(f"Invalid clip '{spec}': expected START-END (e.g. 1:30-2:10)")
        start = parse_timestamp(start_str)
        end = parse_timestamp(end_str)
        if end <= start:
            raise ValueError(f"Invalid clip '{spec}': end must be greater than start")
        clips.append((start, end))
    return clips


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="shorts_factory — Local YouTube Shorts pipeline with YuNet + Whisper + Ollama"
    )
    parser.add_argument("--input", "-i", help="Path to the input video (omit when using --youtube-url)")
    parser.add_argument(
        "--youtube-url",
        "-u",
        help="URL of a video to download and use as input (e.g. a YouTube link)",
    )
    parser.add_argument(
        "--download-dir",
        default="./downloads",
        help="Directory where the downloaded video is saved (default: ./downloads)",
    )
    parser.add_argument(
        "--video-quality",
        default="best",
        help="Max resolution for the download: 'best' (default) or a height like 1080, 720",
    )
    parser.add_argument("--output", "-o", default="./shorts_output", help="Output directory")
    parser.add_argument("--model", "-m", default="llama3", help="Ollama model (llama3, mistral, etc.)")
    parser.add_argument("--max-shorts", "-n", type=int, default=5, help="Maximum number of Shorts")
    parser.add_argument(
        "--min-duration",
        type=float,
        default=SHORT_MIN_SECS,
        help=f"Minimum Short duration in seconds (default: {SHORT_MIN_SECS})",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=SHORT_MAX_SECS,
        help=f"Maximum Short duration in seconds (default: {SHORT_MAX_SECS})",
    )
    parser.add_argument(
        "--clip",
        action="append",
        metavar="START-END",
        help="Manual cut as START-END timestamps (seconds, MM:SS or HH:MM:SS); repeat for multiple "
        "Shorts (e.g. --clip 1:30-2:10 --clip 5:00-5:45). Skips LLM clip selection; "
        "--max-shorts and the duration bounds are ignored.",
    )
    parser.add_argument(
        "--candidates",
        help="JSON file of pre-generated candidates (skips LLM analysis)",
    )
    parser.add_argument(
        "--transcript",
        help="JSON file of a previous transcript (skips Whisper transcription)",
    )
    parser.add_argument(
        "--language",
        default=OUTPUT_LANGUAGE,
        help="Language for the LLM hook/reason text (default: Portuguese)",
    )
    parser.add_argument(
        "--dynamic-subtitles",
        action="store_true",
        help="Use large dynamic subtitles with word highlight, stroke, and shadow",
    )
    parser.add_argument(
        "--subtitles-only",
        action="store_true",
        help="Burn subtitles into the full source video instead of generating Shorts: no cropping, "
        "no LLM analysis, and the original resolution and frame rate are kept (--fps is ignored). "
        "Combine with --dynamic-subtitles for the dynamic style.",
    )
    parser.add_argument(
        "--srt",
        action="store_true",
        help="Also write .srt subtitle files: one for the full source video and one per rendered Short",
    )
    sub = parser.add_argument_group(
        "dynamic subtitle style",
        "Customize the --dynamic-subtitles look. Omitted options keep the current defaults.",
    )
    sub.add_argument(
        "--sub-font",
        help="Path to a .ttf font for dynamic subtitles (default: auto-detected / SUBTITLE_FONT_PATH)",
    )
    sub.add_argument(
        "--sub-font-size",
        type=int,
        help=f"Starting font size in px (default: {DEFAULT_DYNAMIC_SUBTITLE_STYLE.font_px})",
    )
    sub.add_argument(
        "--sub-color",
        help="Color of normal words as R,G,B or #RRGGBB (default: 255,255,255)",
    )
    sub.add_argument(
        "--sub-highlight-color",
        help="Color of the current (karaoke) word as R,G,B or #RRGGBB (default: 255,224,64)",
    )
    sub.add_argument(
        "--sub-stroke-color",
        help="Outline/stroke color as R,G,B or #RRGGBB (default: 0,0,0)",
    )
    sub.add_argument(
        "--sub-stroke-width",
        type=int,
        help=f"Outline/stroke width in px (default: {DEFAULT_DYNAMIC_SUBTITLE_STYLE.stroke_width})",
    )
    sub.add_argument(
        "--sub-y-ratio",
        type=float,
        help="Vertical position of the subtitle block, 0=top to 1=bottom "
        f"(default: {DEFAULT_DYNAMIC_SUBTITLE_STYLE.y_ratio})",
    )
    sub.add_argument(
        "--sub-max-lines",
        type=int,
        help=f"Max subtitle lines (default: {DEFAULT_DYNAMIC_SUBTITLE_STYLE.max_lines})",
    )
    sub.add_argument(
        "--sub-words-per-chunk",
        type=int,
        help="Words shown per static block; the highlight moves across them "
        f"(default: {DEFAULT_DYNAMIC_SUBTITLE_STYLE.words_per_chunk})",
    )
    sub.add_argument(
        "--sub-no-uppercase",
        action="store_true",
        help="Keep the original casing instead of forcing UPPERCASE",
    )
    parser.add_argument(
        "--crop-mode",
        choices=("face", "center", "gameplay", "auto"),
        default="face",
        help="Vertical crop strategy: face tracks faces, center/gameplay use stable center crop, auto is conservative face tracking",
    )
    parser.add_argument(
        "--content-mode",
        choices=("talking-head", "gameplay", "auto"),
        default="talking-head",
        help="Clip-selection prompt mode for talking-head videos, gameplay videos, or automatic guidance",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=DEFAULT_OUTPUT_FPS,
        help=f"Output frame rate; source is downsampled to this (default: {DEFAULT_OUTPUT_FPS}). "
        "Use 0 to keep the source frame rate.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.input and not args.youtube_url:
        print("[ERROR] Provide --input <file> or --youtube-url <url>.")
        sys.exit(1)
    if args.input and args.youtube_url:
        print("[ERROR] Use either --input or --youtube-url, not both.")
        sys.exit(1)

    if args.min_duration < 1:
        print("[ERROR] --min-duration must be >= 1 second.")
        sys.exit(1)
    if args.max_duration <= args.min_duration:
        print("[ERROR] --max-duration must be greater than --min-duration.")
        sys.exit(1)

    if args.subtitles_only and (args.clip or args.candidates):
        print("[ERROR] --subtitles-only renders the full video; remove --clip/--candidates.")
        sys.exit(1)

    manual_clips = None
    if args.clip:
        if args.candidates:
            print("[ERROR] Use either --clip or --candidates, not both.")
            sys.exit(1)
        try:
            manual_clips = parse_clips(args.clip)
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    # Style is parsed before touching heavy deps so bad input fails fast.
    dynamic_subtitle_style = build_dynamic_subtitle_style(args)

    from .download import download_video
    from .pipeline import run

    if args.youtube_url:
        if args.video_quality.lower() == "best":
            max_height = None
        else:
            try:
                max_height = int(args.video_quality)
            except ValueError:
                print("[ERROR] --video-quality must be 'best' or a height like 1080, 720.")
                sys.exit(1)
        input_video = download_video(args.youtube_url, args.download_dir, max_height)
    else:
        input_video = args.input
        if not Path(input_video).exists():
            print(f"[ERROR] File not found: {input_video}")
            sys.exit(1)

    run(
        input_video=input_video,
        output_dir=args.output,
        llm_model=args.model,
        max_shorts=args.max_shorts,
        subtitles_only=args.subtitles_only,
        manual_clips=manual_clips,
        candidates_json=args.candidates,
        transcript_json=args.transcript,
        output_language=args.language,
        dynamic_subtitles=args.dynamic_subtitles,
        crop_mode=args.crop_mode,
        content_mode=args.content_mode,
        output_fps=args.fps,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        generate_srt=args.srt,
        dynamic_subtitle_style=dynamic_subtitle_style,
    )
