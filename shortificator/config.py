"""Project-wide configuration: model choices, geometry, and runtime tunables."""

import os
from typing import Literal

WHISPER_MODEL_SIZE = "large-v3"  # large-v3 for best accuracy; switch to "medium" for speed
# YuNet: lightweight, permissive (Apache-2.0) face detector bundled with OpenCV.
# Downloaded on first use if missing.
YUNET_MODEL_PATH = "models/face_detection_yunet_2023mar.onnx"
YUNET_MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/" "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)

SHORT_TARGET_W = 1080
SHORT_TARGET_H = 1920
DEFAULT_OUTPUT_FPS = 30  # cap output frame rate; source is downsampled to this
SHORT_MIN_SECS = 30  # default minimum clip length; override with --min-duration
SHORT_MAX_SECS = 60  # default maximum clip length; override with --max-duration

SUBTITLE_FONT_SCALE = 1.6
SUBTITLE_COLOR = (255, 255, 255)
SUBTITLE_BG_COLOR = (0, 0, 0)
SUBTITLE_THICKNESS = 3
SUBTITLE_BG_ALPHA = 0.6
# TrueType font for subtitles (cv2.putText/Hershey can't render accents → "?").
# First existing path wins; override via SUBTITLE_FONT_PATH env var.
SUBTITLE_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf",
)
# PIL pixel size roughly maps from the old cv2 scale.
SUBTITLE_FONT_PX = 52
WORDS_PER_SUBTITLE_CHUNK = 5  # how many words per subtitle line

# Language for the LLM-generated "hook"/"reason" fields. Small models (e.g.
# qwen2.5) default to Chinese if not told otherwise. Override via env.
OUTPUT_LANGUAGE = os.environ.get("OUTPUT_LANGUAGE", "Portuguese")

FACE_SMOOTH_WINDOW = 15  # frames to smooth crop movement (avoids jitter)
PIP_VISIBLE_THRESHOLD = 0.15  # if face occupies < 15% of the area, assume PiP/slides mode
SCENE_CHANGE_THRESHOLD = 30.0  # histogram diff to detect scene changes
FACE_DETECT_EVERY = 3  # run face detection every N frames; reuse boxes on the others
# YuNet scales poorly with input size (≈570ms at 4K vs ≈14ms at 960px wide). Detect
# on a downscaled copy and map the boxes back; large faces are still found reliably.
FACE_DETECT_MAX_WIDTH = 960

CropMode = Literal["face", "center", "gameplay", "auto"]
ContentMode = Literal["talking-head", "gameplay", "auto"]
