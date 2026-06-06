"""Single-line CLI progress reporting for long-running steps."""

import time


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m"
    if minutes:
        return f"{minutes:d}m{seconds:02d}s"
    return f"{seconds:d}s"


def print_progress_bar(
    label: str,
    current: int,
    total: int,
    started_at: float,
    finish: bool = False,
    width: int = 28,
) -> None:
    """Render a compact single-line progress bar for long CLI steps."""
    if total <= 0:
        return

    current = min(max(current, 0), total)
    ratio = current / total
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    elapsed = time.monotonic() - started_at

    if finish:
        status = "done" if current >= total else "stopped"
    elif current > 0:
        remaining = elapsed * (total - current) / current
        status = f"ETA {format_duration(remaining)}"
    else:
        status = "ETA --"

    end = "\n" if finish else "\r"
    print(
        f"{label} [{bar}] {ratio * 100:5.1f}% "
        f"({current}/{total} frames, {status}, elapsed {format_duration(elapsed)})",
        end=end,
        flush=True,
    )
