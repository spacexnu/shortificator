"""Speech-to-text transcription with faster-whisper (CUDA)."""

import sys
from pathlib import Path

from .config import WHISPER_MODEL_SIZE
from .models import Segment


def transcribe(video_path: str) -> list[Segment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[ERROR] faster-whisper not installed. Run: pip install faster-whisper")
        sys.exit(1)

    print(f"\n[1/4] Transcribing {Path(video_path).name} with Whisper {WHISPER_MODEL_SIZE}...")
    model = WhisperModel(WHISPER_MODEL_SIZE, device="cuda", compute_type="float16")
    segments_raw, info = model.transcribe(
        video_path,
        language=None,  # autodetect; Whisper infers the audio language
        word_timestamps=True,
        vad_filter=True,
    )
    print(f"      Detected language: {info.language} (prob={info.language_probability:.2f})")

    segments = []
    for seg in segments_raw:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": w.start, "end": w.end})
        segments.append(Segment(start=seg.start, end=seg.end, text=seg.text.strip(), words=words))

    print(f"      {len(segments)} segments transcribed.")
    return segments
