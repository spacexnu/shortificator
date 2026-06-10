# Installation

## System packages

Install FFmpeg:

```bash
sudo apt install ffmpeg
```

Pull the recommended local model:

```bash
ollama pull mistral-small
```

For faster iteration, pull a smaller model too:

```bash
ollama pull qwen2.5:7b
```

## Python dependencies

```bash
poetry install
```

## Verify the environment

```bash
make check-env
```

This checks CUDA availability through CTranslate2, lists local Ollama models, and prints the FFmpeg version.

!!! tip
    Face detection uses YuNet through OpenCV and runs on CPU. CUDA matters most for the faster-whisper transcription step.
