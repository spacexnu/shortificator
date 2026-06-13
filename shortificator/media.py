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


def merge_full_audio(video_path: str, source_path: str, output_path: str) -> subprocess.CompletedProcess:
    """Mux a full-length silent render with the original audio track.

    The audio is stream-copied (no lossy re-encode generation); if the source
    codec doesn't fit the MP4 container, retry re-encoding it as AAC.
    """

    def build_cmd(audio_args: list[str]) -> list[str]:
        return [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
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
            *audio_args,
            "-shortest",
            output_path,
        ]

    result = subprocess.run(build_cmd(["-c:a", "copy"]), capture_output=True, text=True)
    if result.returncode != 0:
        print("      [WARN] Audio stream copy failed; re-encoding audio as AAC.")
        result = subprocess.run(build_cmd(["-c:a", "aac", "-b:a", "192k"]), capture_output=True, text=True)
    return result


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
