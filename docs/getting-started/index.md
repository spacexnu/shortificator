# Getting Started

This section gets the local environment ready and runs the first video through the pipeline.

## Requirements

- Python 3.13+
- Poetry
- FFmpeg and FFprobe
- NVIDIA GPU with CUDA available in WSL2/Linux
- Ollama running locally at `localhost:11434`

## Short path

```bash
poetry install
ollama pull mistral-small
make check-env
poetry run python -m shortificator --input my_video.mp4
```

The legacy entrypoint still works:

```bash
poetry run python shorts_factory.py --input my_video.mp4
```

Both commands call the same CLI.
