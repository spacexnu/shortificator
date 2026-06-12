# Docker

The repo ships a `Dockerfile` and a `compose.yaml` as an alternative to the
local Poetry setup. The stack is fully containerized: the image bundles Python
3.13, FFmpeg, DejaVu fonts and all Python dependencies, and **Ollama runs as a
compose service** — nothing to install on the host besides Docker itself.

The local workflow (`poetry install` + `python -m shortificator`) keeps working
as-is; Docker is optional.

## Requirements

- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop or docker-ce)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  so the containers can use the GPU (transcription and LLM inference)

## Build and verify

```bash
make docker-build
make docker-pull MODEL=mistral-small   # pull an LLM into the Ollama service
make docker-check-env
```

`docker-check-env` runs inside the container and checks CUDA visibility
(CTranslate2) and the Ollama connection, listing the pulled models.

## Run

Through the Makefile, mirroring the local `make run` variables:

```bash
make docker-run INPUT=my_video.mp4 MODEL=mistral-small MAX=5 DYNAMIC=1
```

Or with Docker Compose directly — anything after the service name is passed to
the shortificator CLI:

```bash
docker compose run --rm shortificator \
  --input /videos/my_video.mp4 \
  --model mistral-small \
  --max-shorts 5 \
  --dynamic-subtitles
```

The Ollama service is started automatically when needed. Stop it when you are
done:

```bash
make docker-down
```

## Volumes and paths

| Host | Container | Purpose |
|------|-----------|---------|
| `./` (or `VIDEOS_DIR`) | `/videos` | input videos (read by `--input /videos/...`) |
| `./output` | `/app/output` | generated Shorts, transcripts, candidates |
| `./models` | `/app/models` | YuNet face detection model (auto-downloaded) |
| `whisper-cache` (named volume) | `/root/.cache/huggingface` | Whisper model (~3 GB for `large-v3`), downloaded once |
| `ollama-models` (named volume) | `/root/.ollama` | LLMs pulled with `make docker-pull`, kept across runs |

Set `VIDEOS_DIR=/path/to/videos` to mount a different input directory:

```bash
VIDEOS_DIR=~/videos make docker-run INPUT=gameplay.mp4
```

## Reusing an Ollama on the host

If you already run Ollama on the host and prefer it over the bundled service,
point the container at it:

```bash
OLLAMA_HOST=http://host.docker.internal:11434 make docker-run INPUT=my_video.mp4
```

!!! warning "Host Ollama must listen beyond loopback"
    By default Ollama binds to `127.0.0.1`, which containers cannot reach —
    `docker-check-env` will report *connection refused*. Make it listen on all
    interfaces:

    ```bash
    # one-off
    OLLAMA_HOST=0.0.0.0 ollama serve
    ```

    Or persistently for the systemd service:

    ```bash
    sudo systemctl edit ollama
    # add:
    #   [Service]
    #   Environment="OLLAMA_HOST=0.0.0.0"
    sudo systemctl restart ollama
    ```

    `host.docker.internal` is resolved on Linux/WSL2 via the
    `extra_hosts: host-gateway` entry in `compose.yaml`; on Docker Desktop it
    works out of the box.
