"""End-to-end orchestration: transcribe → analyze → render."""

import json
from pathlib import Path

from .analysis import analyze_with_llm
from .config import DEFAULT_OUTPUT_FPS, OUTPUT_LANGUAGE, SHORT_MAX_SECS, SHORT_MIN_SECS, ContentMode, CropMode
from .media import has_audio_stream
from .models import Segment, ShortCandidate
from .rendering import render_short
from .subtitles import DEFAULT_DYNAMIC_SUBTITLE_STYLE, DynamicSubtitleStyle
from .subtitles.srt import build_srt
from .transcription import transcribe


def run(
    input_video: str,
    output_dir: str,
    llm_model: str = "llama3",
    max_shorts: int = 5,
    skip_analysis: bool = False,
    manual_clips: list[tuple[float, float]] | None = None,
    candidates_json: str | None = None,
    transcript_json: str | None = None,
    output_language: str = OUTPUT_LANGUAGE,
    dynamic_subtitles: bool = False,
    crop_mode: CropMode = "face",
    content_mode: ContentMode = "talking-head",
    output_fps: float = DEFAULT_OUTPUT_FPS,
    min_duration: float = SHORT_MIN_SECS,
    max_duration: float = SHORT_MAX_SECS,
    generate_srt: bool = False,
    dynamic_subtitle_style: DynamicSubtitleStyle = DEFAULT_DYNAMIC_SUBTITLE_STYLE,
):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    video_name = Path(input_video).stem

    with_audio = has_audio_stream(input_video)
    if not with_audio:
        print("[WARN] Input video has no audio stream; Shorts will be generated without sound.")

    # --- Transcription ---
    transcript_path = Path(output_dir) / f"{video_name}_transcript.json"
    if transcript_json:
        # Reuse a previous transcript (skips Whisper, the slowest step)
        with open(transcript_json, encoding="utf-8") as f:
            raw = json.load(f)
        segments = [Segment(**s) for s in raw]
        print(f"[1/4] Transcript loaded from {transcript_json} ({len(segments)} segments).")
    else:
        segments = transcribe(input_video)
        # Save transcript for reference / future reuse
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(
                [{"start": s.start, "end": s.end, "text": s.text, "words": s.words} for s in segments],
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"      Transcript saved to {transcript_path}")

    if generate_srt:
        full_srt_path = Path(output_dir) / f"{video_name}.srt"
        full_srt_path.write_text(build_srt(segments), encoding="utf-8")
        print(f"      Full-video subtitle saved to {full_srt_path.name}")

    # --- LLM analysis ---
    if manual_clips:
        # User picked the cut points; render exactly those clips, no LLM selection.
        candidates = [
            ShortCandidate(start, end, hook=f"Manual clip {i + 1}", reason="User-specified time range")
            for i, (start, end) in enumerate(manual_clips)
        ]
        max_shorts = len(candidates)
        print(f"[2/4] Using {len(candidates)} manual clip(s); skipping LLM analysis.")
    elif candidates_json:
        # Allow reusing a previous analysis (avoids calling the LLM again)
        with open(candidates_json) as f:
            raw = json.load(f)
        candidates = [ShortCandidate(**c) for c in raw]
        print(f"[2/4] Candidates loaded from {candidates_json} ({len(candidates)} items).")
    else:
        candidates = analyze_with_llm(
            segments,
            model=llm_model,
            output_language=output_language,
            max_candidates=max_shorts,
            content_mode=content_mode,
            min_secs=min_duration,
            max_secs=max_duration,
        )

    if not candidates:
        print("[WARN] No candidates found. Try another model or adjust the prompt.")
        return

    # Save candidates
    candidates_path = Path(output_dir) / f"{video_name}_candidates.json"
    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump([vars(c) for c in candidates], f, ensure_ascii=False, indent=2)
    print(f"      Candidates saved to {candidates_path}")

    # --- Rendering ---
    print(f"\n[3/4] Rendering the top {min(max_shorts, len(candidates))} Shorts...")
    rendered = []
    for i, candidate in enumerate(candidates[:max_shorts]):
        out_path = str(Path(output_dir) / f"{video_name}_short_{i + 1:02d}.mp4")
        result = render_short(
            input_video,
            candidate,
            segments,
            out_path,
            i,
            with_audio=with_audio,
            dynamic_subtitles=dynamic_subtitles,
            crop_mode=crop_mode,
            output_fps=output_fps,
            dynamic_subtitle_style=dynamic_subtitle_style,
        )
        if result:
            rendered.append(result)
            if generate_srt:
                srt_path = Path(out_path).with_suffix(".srt")
                srt_path.write_text(build_srt(segments, candidate.start, candidate.end), encoding="utf-8")
                print(f"      Subtitle saved to {srt_path.name}")

    # --- Report ---
    print("\n[4/4] Done!")
    print(f"      {len(rendered)} Shorts generated in: {output_dir}")
    print("\n      Summary:")
    for i, (path, cand) in enumerate(zip(rendered, candidates[:max_shorts], strict=False)):
        duration = cand.end - cand.start
        print(f"      [{i + 1}] {Path(path).name} | {duration:.0f}s | score={cand.score} | {cand.hook}")
