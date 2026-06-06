"""FFmpeg/FFprobe helpers for probing and muxing the rendered clips."""

import subprocess


def has_audio_stream(video_path: str) -> bool:
    """Check via ffprobe whether the video has at least one audio stream."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("[WARN] ffprobe not found; skipping audio validation.")
        return True
    return bool(result.stdout.strip())


def merge_with_audio(
    video_path: str,
    source_path: str,
    start: float,
    end: float,
    output_path: str,
) -> subprocess.CompletedProcess:
    """Mux the silent render with the matching slice of the original audio."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-ss",
        str(start),
        "-to",
        str(end),
        "-i",
        source_path,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        output_path,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def encode_without_audio(video_path: str, output_path: str) -> subprocess.CompletedProcess:
    """Re-encode the silent render when the source video has no audio."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "fast",
        "-an",
        output_path,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)
