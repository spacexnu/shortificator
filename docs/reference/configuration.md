# Configuration

Important defaults live in `shortificator/config.py`.

| Constant | Default | Meaning |
| --- | --- | --- |
| `WHISPER_MODEL_SIZE` | `large-v3` | faster-whisper model |
| `YUNET_MODEL_PATH` | `models/face_detection_yunet_2023mar.onnx` | local face detector model |
| `DEFAULT_OUTPUT_FPS` | `30` | output FPS cap |
| `SHORT_MIN_SECS` | `30` | default minimum clip duration |
| `SHORT_MAX_SECS` | `60` | default maximum clip duration |
| `FACE_SMOOTH_WINDOW` | `15` | frames used to smooth tracking |
| `FACE_DETECT_EVERY` | `3` | detector interval in emitted frames |
| `FACE_DETECT_MAX_WIDTH` | `960` | max width for detection copy |
| `PIP_VISIBLE_THRESHOLD` | `0.15` | face/frame area threshold for PiP classification |
| `WORDS_PER_SUBTITLE_CHUNK` | `5` | static subtitle chunk size |
| `SUBTITLE_FONT_PX` | `52` | static subtitle font size |

## Environment variables

| Variable | Purpose |
| --- | --- |
| `OUTPUT_LANGUAGE` | default language for generated hook/reason text |
| `SUBTITLE_FONT_PATH` | override the TrueType font used for subtitles |
