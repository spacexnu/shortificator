"""Render a single Short: crop, burn subtitles, and mux audio via FFmpeg."""

import os
import tempfile
import time
from pathlib import Path

import cv2

from ..config import DEFAULT_OUTPUT_FPS, FACE_DETECT_EVERY, SHORT_TARGET_H, SHORT_TARGET_W, CropMode
from ..media import encode_without_audio, merge_with_audio
from ..models import Segment, ShortCandidate
from ..progress import print_progress_bar
from ..subtitles import (
    DEFAULT_DYNAMIC_SUBTITLE_STYLE,
    DynamicSubtitleStyle,
    draw_dynamic_subtitle,
    draw_subtitle,
    get_subtitle_chunk_at_time,
    get_words_at_time,
)
from .cropping import crop_frame, detect_video_mode, get_face_detector


def render_short(
    video_path: str,
    candidate: ShortCandidate,
    segments: list[Segment],
    output_path: str,
    index: int,
    with_audio: bool = True,
    dynamic_subtitles: bool = False,
    crop_mode: CropMode = "face",
    output_fps: float = DEFAULT_OUTPUT_FPS,
    dynamic_subtitle_style: DynamicSubtitleStyle = DEFAULT_DYNAMIC_SUBTITLE_STYLE,
) -> str | None:
    print(f"\n      Rendering Short #{index + 1}: {candidate.start:.1f}s → {candidate.end:.1f}s")
    print(f"      Hook: {candidate.hook}")
    print(f"      Crop mode: {crop_mode}")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Cap the output frame rate: most source footage is 60fps but Shorts read fine
    # at 30, so we skip the surplus frames and avoid their crop/subtitle work.
    out_fps = min(fps, output_fps) if output_fps and output_fps > 0 else fps
    frame_step = fps / out_fps
    if out_fps < fps:
        print(f"      Output FPS: {out_fps:.0f} (source {fps:.0f})")

    start_frame = int(candidate.start * fps)
    end_frame = int(candidate.end * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    use_face_tracking = crop_mode in ("face", "auto")
    detector = get_face_detector() if use_face_tracking else None

    out_w, out_h = SHORT_TARGET_W, SHORT_TARGET_H

    # Temporary video file (without audio)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
        tmp_video_path = tmp_video.name

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(tmp_video_path, fourcc, out_fps, (out_w, out_h))

    cx_history, cy_history = [], []
    frame_idx = start_frame
    next_emit = float(start_frame)
    emitted = 0
    total_frames = max(1, end_frame - start_frame + 1)
    render_started_at = time.monotonic()
    last_progress_update = 0.0
    face_boxes: list = []  # keep the previous detection across frames between runs

    print_progress_bar("      Frames", 0, total_frames, render_started_at)

    while frame_idx <= end_frame:
        # Decode (read) only the frames we keep; merely advance past the rest with
        # grab(), which skips the costly colour conversion of the dropped frames.
        emit = frame_idx >= round(next_emit)
        if not emit:
            if not cap.grab():
                break
            frame_idx += 1
            continue

        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps

        # Detect faces every N kept frames; on the others reuse the last detection
        # to avoid the crop snapping back to center (jitter).
        if detector is not None and emitted % FACE_DETECT_EVERY == 0:
            face_boxes = detector.detect(frame)

        detected_video_mode = detect_video_mode(frame, face_boxes) if use_face_tracking else crop_mode
        x1, y1, x2, y2 = crop_frame(
            frame,
            face_boxes,
            detected_video_mode,
            crop_mode,
            cx_history,
            cy_history,
        )

        cropped = frame[y1:y2, x1:x2]
        resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)

        # Subtitle
        if dynamic_subtitles:
            subtitle_words, active_word_idx = get_subtitle_chunk_at_time(
                segments, current_time, dynamic_subtitle_style.words_per_chunk
            )
            resized = draw_dynamic_subtitle(
                resized, subtitle_words, active_word_idx, out_h, out_w, dynamic_subtitle_style
            )
        else:
            subtitle_text = get_words_at_time(segments, current_time)
            resized = draw_subtitle(resized, subtitle_text, out_h, out_w)

        writer.write(resized)
        emitted += 1
        next_emit += frame_step
        frame_idx += 1
        processed_frames = frame_idx - start_frame
        now = time.monotonic()
        if now - last_progress_update >= 0.5 or processed_frames >= total_frames:
            print_progress_bar("      Frames", processed_frames, total_frames, render_started_at)
            last_progress_update = now

    writer.release()
    cap.release()
    print_progress_bar("      Frames", frame_idx - start_frame, total_frames, render_started_at, finish=True)

    final_path = output_path
    if with_audio:
        # Merge video with original audio via FFmpeg
        print("      Merging audio with FFmpeg...")
        result = merge_with_audio(tmp_video_path, video_path, candidate.start, candidate.end, final_path)
    else:
        # No audio in the source video: just re-encode the video.
        print("      Re-encoding video (no audio) with FFmpeg...")
        result = encode_without_audio(tmp_video_path, final_path)
    os.unlink(tmp_video_path)

    if result.returncode != 0:
        print(f"      [FFmpeg ERROR] {result.stderr[-300:]}")
        return None

    size_mb = Path(final_path).stat().st_size / (1024 * 1024)
    print(f"      ✓ {Path(final_path).name} ({size_mb:.1f} MB)")
    return final_path
