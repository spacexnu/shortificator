# shortificator

[![CI](https://github.com/spacexnu/shortificator/actions/workflows/ci.yml/badge.svg)](https://github.com/spacexnu/shortificator/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/spacexnu/shortificator/graph/badge.svg)](https://codecov.io/gh/spacexnu/shortificator)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)

[Documentation](https://spacexnu.github.io/shortificator/)

A fully local pipeline that turns long videos into vertical **YouTube Shorts** — no paid external APIs. It runs on your own machine and uses the GPU via CUDA.

## Demo

From a long source video, shortificator picks the best moments and renders
vertical, captioned Shorts:

<table>
  <tr>
    <th>Source video</th>
    <th>Generated Short</th>
  </tr>
  <tr>
    <td><img src="assets/shortificator-sample.gif" alt="Source sample video" width="480"></td>
    <td><img src="assets/shortificator-sample_short_01.gif" alt="Generated vertical Short" width="270"></td>
  </tr>
</table>

## How it works

```
input.mp4  (or a YouTube URL via yt-dlp → downloaded to --download-dir)
   │
   ├─ 1. Transcribe        faster-whisper (large-v3, CUDA, word timestamps)
   ├─ 2. Analyze clips     Ollama LLM → JSON candidates (start, end, hook, score)
   ├─ 3. Reframe & caption YuNet face crop + OpenCV subtitles
   └─ 4. Render            FFmpeg (CRF 18, AAC 192k) → output/*_short_NN.mp4
```

The frame-by-frame render step prints a single-line progress bar with percentage,
processed frames, ETA, and elapsed time.

## Requirements

- **Python 3.13+**
- **[Poetry](https://python-poetry.org/)** for dependency management
- **FFmpeg** (with `ffprobe`) installed on the system
- **NVIDIA GPU + CUDA** (the Whisper transcription step runs on `cuda`)
- **[Ollama](https://ollama.com/)** running locally at `localhost:11434`

Install the system-level tools:

```bash
# Ubuntu / WSL2
sudo apt install ffmpeg

# Pull an LLM for the analysis step
ollama pull mistral-small
ollama pull qwen2.5:7b  # optional: faster iteration model
```

> **Note on CUDA:** transcription uses faster-whisper, which runs on CUDA via
> CTranslate2 (no PyTorch required). If the GPU is unavailable it falls back to
> being slow on CPU; make sure the NVIDIA cuBLAS/cuDNN runtime libraries are
> installed for GPU acceleration. Face detection (YuNet) and rendering run on CPU.

## Installation

```bash
poetry install
```

Verify the environment is ready:

```bash
make check-env
```

This checks CUDA availability, lists Ollama models, and prints the FFmpeg version.

### Docker (optional)

If you prefer containers, the repo ships a `Dockerfile` and a `compose.yaml`.
The image bundles Python, FFmpeg, fonts and all Python dependencies — no Poetry
or local Python setup needed. The local Poetry workflow above keeps working;
Docker is just an alternative.

Ollama also runs as a compose service, so **nothing besides Docker needs to be
installed on the host**. The only extra requirements are
[Docker](https://docs.docker.com/get-docker/) and the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
(GPU is used by both transcription and the LLM).

```bash
make docker-build                          # build the image
make docker-pull MODEL=mistral-small      # pull an LLM into the Ollama service
make docker-check-env                      # verify CUDA + Ollama from inside the container
make docker-run INPUT=my_video.mp4 MODEL=mistral-small
make docker-down                           # stop the Ollama service when done
```

Or with Docker Compose directly (any CLI flag works after the service name):

```bash
docker compose run --rm shortificator \
  --input /videos/my_video.mp4 \
  --model mistral-small \
  --max-shorts 5
```

Input videos are read from the repo root by default, mounted at `/videos`
inside the container (set `VIDEOS_DIR=/path/to/videos` to change it). Outputs
land in `./output` on the host, the YuNet model is cached in `./models`, and
the Whisper model (~3 GB for `large-v3`) and pulled LLMs are kept in named
Docker volumes so they download only once.

> **Reusing a host Ollama:** if you already run Ollama on the host and don't
> want the containerized one, set
> `OLLAMA_HOST=http://host.docker.internal:11434` when invoking compose or
> make. Note that the host Ollama must listen beyond loopback for containers
> to reach it (start it with `OLLAMA_HOST=0.0.0.0 ollama serve`).

## Usage

The pipeline is a Python package. Run it as a module:

```bash
poetry run python -m shortificator --input my_video.mp4
```

> The legacy entrypoint `python shorts_factory.py ...` still works and is
> equivalent — it is a thin shim kept for backward compatibility.

Download from a URL and use it as input (via `yt-dlp`). Provide either
`--input` or `--youtube-url`, not both:

```bash
poetry run python -m shortificator \
  --youtube-url "https://www.youtube.com/watch?v=XXXX" \
  --download-dir ./downloads \
  --video-quality best        # or 1080, 720 to cap the resolution
```

The video is saved to `--download-dir` (default `./downloads`) and then runs
through the normal pipeline.

Full run with all options:

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --output ./output \
  --model mistral-small \
  --max-shorts 5 \
  --crop-mode face \
  --content-mode talking-head \
  --dynamic-subtitles
```

Gameplay run:

```bash
poetry run python -m shortificator \
  --input gameplay.mp4 \
  --output ./output \
  --model mistral-small \
  --max-shorts 5 \
  --crop-mode gameplay \
  --content-mode gameplay \
  --dynamic-subtitles
```

Reuse a previous transcript (skips Whisper, the slowest step — useful when
iterating on the analysis/render steps for the same video):

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --transcript output/my_video_transcript.json
```

Reuse a previous LLM analysis (skips both transcription *and* analysis, just re-renders):

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --transcript output/my_video_transcript.json \
  --candidates output/my_video_candidates.json
```

> The transcript is saved automatically on every full run (`output/{name}_transcript.json`),
> so you can pass it back via `--transcript` on later runs without re-running Whisper.

### CLI options

| Flag                  | Default            | Description                                       |
|-----------------------|--------------------|---------------------------------------------------|
| `--input`, `-i`       | —                  | Path to the input video (required unless `--youtube-url` is used) |
| `--youtube-url`, `-u` | —                  | URL to download with yt-dlp and use as input (mutually exclusive with `--input`) |
| `--download-dir`      | `./downloads`      | Directory where the downloaded video is saved     |
| `--video-quality`     | `best`             | Max download resolution: `best` or a height like `1080`, `720` |
| `--output`, `-o`      | `./shorts_output`  | Output directory                                  |
| `--model`, `-m`       | `llama3`           | Ollama model. Recommended: `mistral-small` for quality, `qwen2.5:7b` for speed |
| `--max-shorts`, `-n`  | `5`                | Maximum number of Shorts to render                |
| `--min-duration`      | `30`               | Minimum Short duration in seconds                 |
| `--max-duration`      | `60`               | Maximum Short duration in seconds                 |
| `--candidates`        | —                  | JSON of pre-generated candidates (skips analysis) |
| `--transcript`        | —                  | JSON of a previous transcript (skips Whisper)     |
| `--language`          | `Portuguese`       | Language for the LLM `hook`/`reason` text (or set `OUTPUT_LANGUAGE`) |
| `--dynamic-subtitles` | `false`            | Large subtitle style with word highlight, stroke, and shadow |
| `--srt`               | `false`            | Also write `.srt` files: one for the full video and one per Short |
| `--crop-mode`         | `face`             | Crop strategy: `face`, `center`, `gameplay`, `auto` |
| `--content-mode`      | `talking-head`     | LLM selection mode: `talking-head`, `gameplay`, `auto` |
| `--fps`               | `30`               | Output frame rate; the source is downsampled to it (use `0` to keep the source rate) |

#### Dynamic subtitle style

When `--dynamic-subtitles` is on, the look is fully configurable. Every option
below defaults to the current built-in style, so omitting them reproduces the
previous output exactly.

| Flag                    | Default       | Description                                  |
|-------------------------|---------------|----------------------------------------------|
| `--sub-font`            | auto-detected | Path to a `.ttf` font (also via `SUBTITLE_FONT_PATH`) |
| `--sub-font-size`       | `78`          | Starting font size in px (auto-shrinks to fit) |
| `--sub-color`           | `255,255,255` | Normal word color (`R,G,B` or `#RRGGBB`)     |
| `--sub-highlight-color` | `255,224,64`  | Current (karaoke) word color                 |
| `--sub-stroke-color`    | `0,0,0`       | Outline/stroke color                         |
| `--sub-stroke-width`    | `5`           | Outline/stroke width in px                   |
| `--sub-y-ratio`         | `0.74`        | Vertical position (`0`=top, `1`=bottom)      |
| `--sub-max-lines`       | `2`           | Maximum subtitle lines                       |
| `--sub-words-per-chunk` | `4`           | Words per static block; highlight moves across them |
| `--sub-no-uppercase`    | off           | Keep original casing instead of UPPERCASE    |

Dynamic subtitles show a **fixed block** of `--sub-words-per-chunk` words at a
time. The block stays put while only the highlight color moves across it, and
advances to the next group when speech crosses into it (CapCut-style). This reads
much more easily than scrolling the text word by word. The last block is held
during short pauses to avoid flicker.

```bash
poetry run python -m shortificator \
  --input my_video.mp4 \
  --dynamic-subtitles \
  --sub-color "#FFFFFF" \
  --sub-highlight-color "0,200,255" \
  --sub-font-size 84 \
  --sub-y-ratio 0.8
```

### Face and gameplay modes

Use `--crop-mode face --content-mode talking-head` for videos where the speaker's
face is the main visual subject. This tracks the face with YuNet and centers the
9:16 crop around the detected face.

This is the default profile. If you omit both flags, the pipeline behaves as
`--crop-mode face --content-mode talking-head`.

Use `--crop-mode gameplay --content-mode gameplay` for game footage. This skips
face detection and uses a stable center crop, which is usually safer for preserving crosshair,
HUD, action, and screen context. The gameplay content mode also changes the LLM
prompt to look for tension, combat, surprise, failures, wins, and player reactions
instead of only spoken insights.

`--crop-mode center` is a generic stable center crop. `--crop-mode auto` is
currently conservative and uses the same face-tracking path as `face`; keep using
explicit `face` or `gameplay` when you already know the video type.

## LLM analysis: structured output

The analysis step (`shortificator.analysis.analyze_with_llm`) relies on Ollama's
**structured outputs**. Instead of asking the model to "return only JSON" and
hoping for the best, it passes an explicit JSON Schema from `build_analysis_schema(...)`
to `ollama.chat(..., format=...)`.

### Windowed selection for temporal coverage

Small models tend to cluster all their picks in a single region (often wherever
they latched on first), so a whole-video prompt frequently returns clips bunched
together and a candidate count that swings between runs. To avoid this, the
analysis splits the video into `--max-shorts` consecutive time windows and queries
the model **once per window**, asking for a couple of candidates each. The pooled
results are then sorted by score, de-duplicated by overlap, and trimmed to
`--max-shorts`.

The effect is that `--max-shorts 5` reliably yields clips spread across the whole
video (e.g. one near the start, middle, and end) instead of five near-identical
moments. The trade-off is one LLM call per window instead of a single call; each
call is cheaper because it only sees its slice of the transcript, and the result
can still be cached and reused with `--candidates`.

Recommended models:

- `mistral-small`: preferred default for higher-quality editorial choices. It is slower,
  but the analysis result can be reused with `--candidates`, so the extra latency is
  usually acceptable after the first pass.
- `qwen2.5:7b`: faster option for prompt iteration, preview runs, and quick candidate
  generation.
- `llama3`: generic fallback if the preferred models are unavailable.

This matters with smaller models (e.g. `qwen2.5:7b`):

- Without `format`, the model often replies with prose (a summary) instead of JSON.
- With `format="json"`, the output is *syntactically* valid JSON but the model may
  invent its own shape (`video_title`, `key_points`, …), so `candidates` ends up empty.
- With the structured schema, the model is constrained to the exact expected fields
  (`start`, `end`, `hook`, `reason`, `score`), so parsing is reliable.

The prompt also enforces a **hard duration requirement**. The default window is
`30-60s`, which keeps clips short enough for fast Shorts/Reels pacing while
preserving enough context for technical ideas. Tune it per platform with
`--min-duration` / `--max-duration` (e.g. `--max-duration 90` for Reels).

If you still get few or no candidates, try a different/larger model via `--model`.

## Face detection model

Face tracking uses **YuNet** (`cv2.FaceDetectorYN`), a lightweight, permissively
licensed (Apache-2.0) detector bundled with OpenCV. The model file
(`face_detection_yunet_2023mar.onnx`, ~230 KB) is downloaded automatically to
`models/` on first use, so there is no manual setup.

YuNet runs on CPU, needs no PyTorch/CUDA, and tracks the main speaker's face well
in talking-head footage. For content with very small faces (e.g. tiny PiP
facecams) a heavier detector can be more robust; that trade-off was accepted in
favor of a fully permissive, low-friction install.

## Output files

For an input named `my_video.mp4`, each run writes to the output directory:

| File                              | Content                                  |
|-----------------------------------|------------------------------------------|
| `my_video_transcript.json`        | Full transcript with word timestamps     |
| `my_video_candidates.json`        | LLM clip candidates with scores          |
| `my_video_short_01.mp4` … `_NN`   | Rendered vertical Shorts                 |
| `my_video.srt` *(with `--srt`)*   | Subtitles for the full source video      |
| `my_video_short_01.srt` … *(with `--srt`)* | Subtitles per Short (clip-relative timing) |

## Project layout

The code is organized as a `shortificator/` package, grouped by pipeline stage.
Pure logic (data models, clip selection, prompts, subtitle timing/styling) is
kept free of heavy runtime dependencies, which keeps those modules fast to import
and easy to unit-test without a GPU.

```
shortificator/
├── shorts_factory.py       # backward-compatible entrypoint (thin shim)
├── pyproject.toml          # Poetry project + tool config (ruff, pytest, coverage)
├── Makefile                # common commands
├── README.md               # this file
├── CONTRIBUTING.md         # contribution guidelines
└── shortificator/          # the package
    ├── cli.py              # argparse + entrypoint
    ├── config.py           # constants and runtime configuration
    ├── pipeline.py         # run() orchestrator
    ├── transcription.py    # faster-whisper
    ├── download.py         # yt-dlp
    ├── media.py            # ffprobe + ffmpeg
    ├── analysis/           # prompts, candidate selection, Ollama call
    ├── subtitles/          # styling, word timing, burned-in rendering
    └── rendering/          # YuNet cropping + final Short render
```

## Development

Common tasks are wrapped in the `Makefile`:

```bash
make help        # list available targets
make install     # poetry install
make check-env   # verify CUDA, Ollama and FFmpeg
make run         # run the pipeline (override INPUT, OUTPUT, MODEL, MAX, CROP_MODE, CONTENT_MODE, DYNAMIC)
make lint        # ruff check
make lint-fix    # ruff check --fix
make fmt         # ruff format
make fmt-check   # ruff format --check
make typecheck   # compile all sources to catch syntax errors
make test        # pytest (with coverage summary)
make cov         # pytest + XML/HTML coverage reports
make check       # lint + format check + syntax check
make clean       # remove generated outputs and caches
```

`make run` variables can be overridden inline:

```bash
make run INPUT=talk.mp4 OUTPUT=./output MODEL=mistral-small MAX=3 CROP_MODE=face CONTENT_MODE=talking-head
make run INPUT=dayz.mp4 OUTPUT=./output MODEL=mistral-small MAX=3 CROP_MODE=gameplay CONTENT_MODE=gameplay DYNAMIC=1
```

### Rendering performance

The render stage re-encodes frame by frame on CPU, so a few things keep it
practical, especially on weaker machines:

- **Face detection runs on a downscaled copy** of each frame. YuNet costs ~570ms
  on a 4K frame but ~14ms at 960px wide, so detection is no longer the bottleneck.
- **Output is capped to 30 fps** (`--fps`). Most source footage is 60 fps; the
  surplus frames are skipped with a cheap `grab()`, roughly halving render time.
- **Dynamic subtitle layouts are cached** per word block, so the font-fit pass
  only runs when the on-screen text actually changes.

For 4K/60fps sources the heaviest remaining cost is simply decoding every frame.
If you need more speed, transcode the source to 1080p first.

### Testing & coverage

The test suite targets the pure-logic modules and uses mocks for the external
boundaries (Ollama, FFmpeg, the rendering stages), so it runs in well under a
second without a GPU, models, or network access:

```bash
make test          # run the suite
make cov           # also write coverage.xml and htmlcov/
```

Coverage is configured in `pyproject.toml` (`pytest` runs with `--cov` by
default). The heavy I/O modules (frame rendering, face cropping, Whisper,
yt-dlp) require real video/GPU and are intentionally left for manual/integration
runs rather than the unit suite.

## Issues & feedback

Found a bug, hit a problem, or have an idea to improve the project? Please
[open an issue](https://github.com/spacexnu/shortificator/issues). It helps to include:

- what you expected to happen and what actually happened;
- the exact command you ran;
- your environment (OS, Python version, GPU/CUDA, Ollama model);
- any error output or stack trace.

Feature ideas and suggestions are equally welcome, just open an issue describing the
use case. For questions about contributing code, see below.

## Contributing

Contributions are welcome! Please read the [contribution guidelines](CONTRIBUTING.md)
before opening a pull request.

## Documentation

The full documentation is available at
[https://spacexnu.github.io/shortificator/](https://spacexnu.github.io/shortificator/).

## License

Released under the [MIT License](LICENSE).

All runtime dependencies are permissively licensed (MIT / BSD / Apache-2.0 /
HPND / Unlicense), and face detection uses the Apache-2.0 YuNet model, so the
project can be used and distributed under MIT without copyleft obligations.
