# Clip Analysis

The analysis step uses Ollama structured outputs instead of asking the model to return "JSON only".

`build_analysis_schema()` creates a JSON Schema and `analyze_with_llm()` passes that schema to:

```python
ollama.chat(..., format=schema)
```

This keeps smaller models from inventing unrelated response shapes.

## Windowed selection

Small models can cluster every candidate in the same part of a long transcript. shortificator avoids that by splitting the transcript into consecutive time windows based on `--max-shorts`.

Each window requests a small set of candidates. The pipeline then:

1. pools all candidates;
2. sorts them by score;
3. removes heavy overlaps;
4. trims the list to `--max-shorts`.

This gives better temporal coverage across the video.

## Duration fitting

The prompt asks the model to respect `--min-duration` and `--max-duration`, but models are not perfectly reliable. `fit_clip_window()` adjusts short or long candidates around their center and clamps them to the source duration.

Defaults:

```text
--min-duration 30
--max-duration 60
```

## Manual clips

When you already know where the cuts should be, skip the LLM entirely with `--clip START-END` (repeatable):

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --clip 1:30-2:10 \
  --clip 5:00-5:45
```

Timestamps accept plain seconds (`90`, `90.5`), `MM:SS`, or `HH:MM:SS` (fractions allowed).

With `--clip`:

- every clip is rendered in the order given — `--max-shorts` and the duration bounds do not apply;
- transcription still runs (burned subtitles and `--srt` need the word timestamps), and reusing a saved transcript with `--transcript` works as usual;
- `--candidates` cannot be combined with `--clip`, since both define the cuts.

## Model choices

- `mistral-small`: recommended for quality.
- `qwen2.5:7b`: useful for faster prompt iteration.
- `llama3`: generic fallback.
