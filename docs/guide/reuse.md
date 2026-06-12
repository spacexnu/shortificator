# Reusing Artifacts

Every full run saves the expensive intermediate files. Use them when tuning crop, subtitle style, FPS, or output duration.

## Skip Whisper

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --transcript output/my_video_transcript.json
```

## Skip Whisper and Ollama

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --transcript output/my_video_transcript.json \
  --candidates output/my_video_candidates.json
```

This is the fastest rerender path.

!!! tip
    If you want specific cut points instead of reusing the LLM picks, pass them
    directly with `--clip START-END` (repeatable) — see
    [Clip Analysis](clip-analysis.md#manual-clips). It combines with
    `--transcript`, but not with `--candidates`.

## Typical style iteration

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --transcript output/my_video_transcript.json \
  --candidates output/my_video_candidates.json \
  --dynamic-subtitles \
  --sub-highlight-color "#20C997" \
  --sub-font-size 84 \
  --sub-y-ratio 0.8
```
