"""Burn subtitles into the full source video, keeping resolution and frame rate."""

import os
import tempfile
import time
from pathlib import Path

import cv2

from ..media import encode_without_audio, merge_full_audio
from ..models import Segment
from ..progress import print_progress_bar
from ..subtitles import (
    DEFAULT_DYNAMIC_SUBTITLE_STYLE,
    DynamicSubtitleStyle,
    draw_dynamic_subtitle,
    draw_subtitle,
    get_subtitle_chunk_at_time,
    get_words_at_time,
)


def render_subtitled_video(
    video_path: str,
    segments: list[Segment],
    output_path: str,
    with_audio: bool = True,
    dynamic_subtitles: bool = False,
    dynamic_subtitle_style: DynamicSubtitleStyle = DEFAULT_DYNAMIC_SUBTITLE_STYLE,
) -> str | None:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # FRAME_COUNT is an estimate on some containers; the read loop is the real stop.
    total_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))

    print(f"      Source: {width}x{height} @ {fps:.2f}fps (kept as-is)")

    # Temporary video file (without audio)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
        tmp_video_path = tmp_video.name

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(tmp_video_path, fourcc, fps, (width, height))

    frame_idx = 0
    render_started_at = time.monotonic()
    last_progress_update = 0.0

    print_progress_bar("      Frames", 0, total_frames, render_started_at)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps

        if dynamic_subtitles:
            subtitle_words, active_word_idx = get_subtitle_chunk_at_time(
                segments, current_time, dynamic_subtitle_style.words_per_chunk
            )
            frame = draw_dynamic_subtitle(
                frame, subtitle_words, active_word_idx, height, width, dynamic_subtitle_style
            )
        else:
            subtitle_text = get_words_at_time(segments, current_time)
            frame = draw_subtitle(frame, subtitle_text, height, width)

        writer.write(frame)
        frame_idx += 1
        now = time.monotonic()
        if now - last_progress_update >= 0.5 or frame_idx >= total_frames:
            print_progress_bar("      Frames", frame_idx, total_frames, render_started_at)
            last_progress_update = now

    writer.release()
    cap.release()
    print_progress_bar("      Frames", frame_idx, max(total_frames, frame_idx), render_started_at, finish=True)

    if with_audio:
        # Merge video with original audio via FFmpeg
        print("      Merging audio with FFmpeg...")
        result = merge_full_audio(tmp_video_path, video_path, output_path)
    else:
        # No audio in the source video: just re-encode the video.
        print("      Re-encoding video (no audio) with FFmpeg...")
        result = encode_without_audio(tmp_video_path, output_path)
    os.unlink(tmp_video_path)

    if result.returncode != 0:
        print(f"      [FFmpeg ERROR] {result.stderr[-300:]}")
        return None

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"      ✓ {Path(output_path).name} ({size_mb:.1f} MB)")
    return output_path
