# CLI Reference

Run either entrypoint:

```bash
poetry run python -m shortificator --help
poetry run python shorts_factory.py --help
```

## Main options

| Flag | Default | Description |
| --- | --- | --- |
| `--input`, `-i` | none | input video path; required unless `--youtube-url` is used |
| `--youtube-url`, `-u` | none | URL to download with yt-dlp |
| `--download-dir` | `./downloads` | destination for downloaded videos |
| `--video-quality` | `best` | `best` or max height such as `1080` |
| `--output`, `-o` | `./shorts_output` | output directory |
| `--model`, `-m` | `llama3` | Ollama model name |
| `--max-shorts`, `-n` | `5` | maximum number of Shorts to render |
| `--min-duration` | `30` | minimum clip duration in seconds |
| `--max-duration` | `60` | maximum clip duration in seconds |
| `--clip` | none | manual cut as `START-END` (seconds, `MM:SS` or `HH:MM:SS`); repeatable, skips LLM analysis |
| `--transcript` | none | saved transcript JSON; skips Whisper |
| `--candidates` | none | saved candidates JSON; skips LLM analysis |
| `--language` | `Portuguese` | language for hook/reason text |
| `--dynamic-subtitles` | off | use fixed-block highlighted subtitles |
| `--srt` | off | write SRT files |
| `--crop-mode` | `face` | `face`, `center`, `gameplay`, `auto` |
| `--content-mode` | `talking-head` | `talking-head`, `gameplay`, `auto` |
| `--fps` | `30` | output FPS; use `0` to keep source FPS |

## Dynamic subtitle options

| Flag | Default |
| --- | --- |
| `--sub-font` | auto-detected |
| `--sub-font-size` | `78` |
| `--sub-color` | `255,255,255` |
| `--sub-highlight-color` | `255,224,64` |
| `--sub-stroke-color` | `0,0,0` |
| `--sub-stroke-width` | `5` |
| `--sub-y-ratio` | `0.74` |
| `--sub-max-lines` | `2` |
| `--sub-words-per-chunk` | `4` |
| `--sub-no-uppercase` | off |
