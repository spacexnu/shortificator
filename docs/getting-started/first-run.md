# First Run

Run the package module with an input video:

```bash
poetry run python -m shortificator --input my_video.mp4
```

By default, the pipeline writes generated files to `./shorts_output`.

## Download from YouTube

Provide `--youtube-url` instead of `--input`:

```bash
poetry run python -m shortificator \
  --youtube-url "https://www.youtube.com/watch?v=XXXX" \
  --download-dir ./downloads \
  --video-quality best
```

Use a numeric height to cap the download resolution:

```bash
--video-quality 1080
```

## Common profiles

=== "Talking head"

    ```bash
    poetry run python -m shortificator \
      --input talk.mp4 \
      --model mistral-small \
      --crop-mode face \
      --content-mode talking-head \
      --dynamic-subtitles
    ```

=== "Gameplay"

    ```bash
    poetry run python -m shortificator \
      --input gameplay.mp4 \
      --model mistral-small \
      --crop-mode gameplay \
      --content-mode gameplay \
      --dynamic-subtitles
    ```
