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
