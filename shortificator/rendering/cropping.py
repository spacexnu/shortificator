"""Video-mode detection and 9:16 crop computation (with face tracking)."""

import urllib.request
from pathlib import Path

import cv2
import numpy as np

from ..config import (
    FACE_DETECT_MAX_WIDTH,
    FACE_SMOOTH_WINDOW,
    PIP_VISIBLE_THRESHOLD,
    SHORT_TARGET_H,
    SHORT_TARGET_W,
    YUNET_MODEL_PATH,
    YUNET_MODEL_URL,
    CropMode,
)

Box = tuple[int, int, int, int]


def _ensure_yunet_model() -> str:
    """Return the YuNet model path, downloading it on first use if absent."""
    path = Path(YUNET_MODEL_PATH)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"      Downloading YuNet face model to {path}...")
        urllib.request.urlretrieve(YUNET_MODEL_URL, path)
    return str(path)


def _yunet_faces_to_boxes(faces) -> list[Box]:
    """Convert YuNet's (N, 15) detection array into (x1, y1, x2, y2) boxes."""
    boxes: list[Box] = []
    if faces is None:
        return boxes
    for face in faces:
        x, y, w, h = face[:4]
        boxes.append((int(x), int(y), int(round(x + w)), int(round(y + h))))
    return boxes


class YuNetFaceDetector:
    """OpenCV YuNet face detector (Apache-2.0, CPU-friendly, no torch)."""

    def __init__(self) -> None:
        self._model = cv2.FaceDetectorYN_create(_ensure_yunet_model(), "", (320, 320), 0.6, 0.3, 5000)

    def detect(self, frame: np.ndarray) -> list[Box]:
        h, w = frame.shape[:2]
        scale = FACE_DETECT_MAX_WIDTH / w if w > FACE_DETECT_MAX_WIDTH else 1.0
        if scale != 1.0:
            frame = cv2.resize(frame, (FACE_DETECT_MAX_WIDTH, round(h * scale)))

        sh, sw = frame.shape[:2]
        self._model.setInputSize((sw, sh))
        _, faces = self._model.detect(frame)
        boxes = _yunet_faces_to_boxes(faces)

        if scale != 1.0:
            inv = 1.0 / scale
            boxes = [(round(x1 * inv), round(y1 * inv), round(x2 * inv), round(y2 * inv)) for x1, y1, x2, y2 in boxes]
        return boxes


_face_detector: YuNetFaceDetector | None = None


def get_face_detector() -> YuNetFaceDetector:
    """Return the face detector as a lazily-instantiated singleton."""
    global _face_detector
    if _face_detector is None:
        _face_detector = YuNetFaceDetector()
    return _face_detector


def detect_video_mode(frame: np.ndarray, face_boxes: list) -> str:
    """
    Detect whether the frame is:
    - 'face_only': centered face, no slides
    - 'pip': slides with a smaller face (PiP)
    - 'slides': no face detected
    """
    if not face_boxes:
        return "slides"

    h, w = frame.shape[:2]
    frame_area = h * w

    largest_face = max(face_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    fx1, fy1, fx2, fy2 = largest_face
    face_area = (fx2 - fx1) * (fy2 - fy1)
    face_ratio = face_area / frame_area

    if face_ratio < PIP_VISIBLE_THRESHOLD:
        return "pip"
    return "face_only"


def smooth_crop_coords(history: list, new_val: float, window: int) -> float:
    history.append(new_val)
    if len(history) > window:
        history.pop(0)
    return float(np.mean(history))


def compute_center_crop_for_frame(frame: np.ndarray) -> tuple[int, int, int, int]:
    """Return a stable center 9:16 crop without face detection."""
    fh, fw = frame.shape[:2]
    target_ratio = SHORT_TARGET_W / SHORT_TARGET_H

    crop_h = fh
    crop_w = int(crop_h * target_ratio)
    if crop_w > fw:
        crop_w = fw
        crop_h = int(crop_w / target_ratio)

    x1 = max(0, (fw - crop_w) // 2)
    y1 = max(0, (fh - crop_h) // 2)
    return x1, y1, x1 + crop_w, y1 + crop_h


def compute_crop_for_frame(
    frame: np.ndarray,
    face_boxes: list,
    mode: str,
    cx_history: list,
    cy_history: list,
) -> tuple[int, int, int, int]:
    """
    Return (x1, y1, x2, y2) of the 9:16 crop for the frame.
    Priority: the face. In PiP mode, try to include face + slide area if it fits.
    """
    fh, fw = frame.shape[:2]
    target_ratio = SHORT_TARGET_W / SHORT_TARGET_H  # 9/16

    # Crop height: use the full frame height
    crop_h = fh
    crop_w = int(crop_h * target_ratio)

    if crop_w > fw:
        crop_w = fw
        crop_h = int(crop_w / target_ratio)

    if face_boxes and mode in ("face_only", "pip"):
        largest_face = max(face_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        fx1, fy1, fx2, fy2 = largest_face
        face_cx = (fx1 + fx2) / 2
        face_cy = (fy1 + fy2) / 2
    else:
        face_cx = fw / 2
        face_cy = fh / 2

    # Smooth to avoid jitter
    cx = smooth_crop_coords(cx_history, face_cx, FACE_SMOOTH_WINDOW)
    cy = smooth_crop_coords(cy_history, face_cy, FACE_SMOOTH_WINDOW)

    # Compute crop centered on the face
    x1 = int(cx - crop_w / 2)
    y1 = int(cy - crop_h / 2)

    # Clamp within the frame
    x1 = max(0, min(x1, fw - crop_w))
    y1 = max(0, min(y1, fh - crop_h))
    x2 = x1 + crop_w
    y2 = y1 + crop_h

    return x1, y1, x2, y2


def crop_frame(
    frame: np.ndarray,
    face_boxes: list,
    detected_video_mode: str,
    crop_mode: CropMode,
    cx_history: list,
    cy_history: list,
) -> tuple[int, int, int, int]:
    """Choose the crop strategy for a frame."""
    if crop_mode in ("center", "gameplay"):
        return compute_center_crop_for_frame(frame)

    # "face" and the current conservative "auto" path both use face tracking.
    return compute_crop_for_frame(frame, face_boxes, detected_video_mode, cx_history, cy_history)
