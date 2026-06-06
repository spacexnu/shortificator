"""Video acquisition from remote URLs via yt-dlp."""

import sys
from pathlib import Path

try:
    from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None  # only required when --youtube-url is used


def download_video(
    youtube_url: str,
    download_dir: str,
    max_height: int | None = None,
) -> str:
    """Download a video from a URL with yt-dlp and return the local file path.

    The video is fetched in the best available quality. ``max_height`` caps the
    vertical resolution (e.g. 1080 limits to 1080p); ``None`` means no cap, i.e.
    the highest resolution available.
    """
    if YoutubeDL is None:
        print("[ERROR] yt-dlp not installed. Run: poetry install (or pip install yt-dlp)")
        sys.exit(1)

    Path(download_dir).mkdir(parents=True, exist_ok=True)

    if max_height:
        fmt = f"bestvideo[height<={max_height}]+bestaudio/" f"best[height<={max_height}]/best"
        quality_label = f"<= {max_height}p"
    else:
        fmt = "bestvideo+bestaudio/best"
        quality_label = "best available"

    ydl_opts = {
        "format": fmt,
        "outtmpl": str(Path(download_dir) / "%(title)s [%(id)s].%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    print(f"[0/4] Downloading video ({quality_label}) from {youtube_url} ...")
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        path = ydl.prepare_filename(info)

    # prepare_filename returns the pre-merge extension; reconcile with the
    # merged output (mp4) when yt-dlp remuxed the streams.
    final = Path(path)
    if not final.exists():
        merged = final.with_suffix(".mp4")
        if merged.exists():
            final = merged

    print(f"      Saved to {final}")
    return str(final)
