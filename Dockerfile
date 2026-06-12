FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg for rendering, DejaVu fonts for burned-in subtitles (UTF-8 glyphs)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Runtime dependencies (kept in sync with pyproject.toml).
# nvidia-cublas/cudnn wheels provide the CUDA libs ctranslate2 (faster-whisper)
# needs at runtime; the GPU driver itself is injected by the NVIDIA Container
# Toolkit (--gpus all / compose device reservation).
RUN pip install \
        "faster-whisper>=1.0.0" \
        "opencv-python-headless>=4.9.0" \
        "ollama>=0.3.0" \
        "numpy>=1.26.0" \
        "pillow>=12.2.0,<13.0.0" \
        "yt-dlp>=2024.0.0" \
        "nvidia-cublas-cu12" \
        "nvidia-cudnn-cu12>=9,<10"

ENV LD_LIBRARY_PATH=/usr/local/lib/python3.13/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.13/site-packages/nvidia/cudnn/lib

WORKDIR /app
COPY shortificator/ shortificator/
COPY shorts_factory.py ./

# Fallback for plain `docker run` (compose overrides this to the bundled
# ollama service at http://ollama:11434).
ENV OLLAMA_HOST=http://host.docker.internal:11434

ENTRYPOINT ["python", "-m", "shortificator"]
CMD ["--help"]
