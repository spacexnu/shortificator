import numpy as np

from shortificator.rendering import cropping


class TestYunetFacesToBoxes:
    def test_none_yields_empty(self):
        assert cropping._yunet_faces_to_boxes(None) == []

    def test_converts_xywh_to_corners(self):
        # YuNet rows are [x, y, w, h, <10 landmark/score values>].
        faces = np.array([[10.0, 20.0, 30.0, 40.0] + [0.0] * 11])
        assert cropping._yunet_faces_to_boxes(faces) == [(10, 20, 40, 60)]

    def test_multiple_faces(self):
        faces = np.array(
            [
                [0.0, 0.0, 50.0, 50.0] + [0.0] * 11,
                [100.0, 100.0, 20.0, 20.0] + [0.0] * 11,
            ]
        )
        assert cropping._yunet_faces_to_boxes(faces) == [(0, 0, 50, 50), (100, 100, 120, 120)]


class _FakeYuNetModel:
    def __init__(self):
        self.input_size = None

    def setInputSize(self, size):  # noqa: N802 - mirrors the OpenCV API
        self.input_size = size

    def detect(self, frame):
        # One face at (10, 20, w=30, h=40) in the (possibly downscaled) frame.
        return 1, np.array([[10.0, 20.0, 30.0, 40.0] + [0.0] * 11])


class TestYuNetDetectScaling:
    def _detector(self):
        det = cropping.YuNetFaceDetector.__new__(cropping.YuNetFaceDetector)
        det._model = _FakeYuNetModel()
        return det

    def test_downscales_input_and_rescales_boxes(self):
        from shortificator.config import FACE_DETECT_MAX_WIDTH

        det = self._detector()
        boxes = det.detect(np.zeros((2160, 3840, 3), dtype=np.uint8))
        # YuNet was fed the downscaled width, not the original 4K width.
        assert det._model.input_size[0] == FACE_DETECT_MAX_WIDTH
        # scale = 960/3840 = 0.25 → boxes mapped back by 4x.
        assert boxes == [(40, 80, 160, 240)]

    def test_small_frame_is_not_downscaled(self):
        det = self._detector()
        boxes = det.detect(np.zeros((360, 640, 3), dtype=np.uint8))
        assert det._model.input_size == (640, 360)
        assert boxes == [(10, 20, 40, 60)]


class TestGetFaceDetector:
    def test_is_a_cached_singleton(self, monkeypatch):
        created = []

        class FakeDetector:
            def __init__(self):
                created.append(1)

        monkeypatch.setattr(cropping, "_face_detector", None)
        monkeypatch.setattr(cropping, "YuNetFaceDetector", FakeDetector)

        first = cropping.get_face_detector()
        second = cropping.get_face_detector()
        assert first is second  # cached, instantiated once
        assert len(created) == 1
