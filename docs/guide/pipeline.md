# Pipeline

shortificator is split into four stages.

## 1. Transcription

`shortificator.transcription.transcribe()` uses faster-whisper with the `large-v3` model and word timestamps.

The resulting transcript is saved as:

```text
output/{name}_transcript.json
```

## 2. Clip analysis

`shortificator.analysis.llm.analyze_with_llm()` sends transcript windows to Ollama and expects structured JSON candidates:

```text
start, end, hook, reason, score
```

## 3. Reframing and subtitles

`shortificator.rendering.short.render_short()` crops the source to a 9:16 frame and burns subtitles into the video frames.

The crop behavior depends on `--crop-mode`. The LLM prompt depends on `--content-mode`.

## 4. Final render

FFmpeg muxes the rendered video stream with audio from the source and writes final MP4 files:

```text
output/{name}_short_01.mp4
output/{name}_short_02.mp4
```

With `--srt`, it also writes subtitle files for the full source and for each generated Short.
