from types import SimpleNamespace

import numpy as np

from shortificator.models import Segment
from shortificator.rendering import subtitled


class _FakeCapture:
    """Minimal cv2.VideoCapture stand-in yielding a fixed number of frames."""

    _PROPS = {
        # cv2.CAP_PROP_FPS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_COUNT
        5: 30.0,
        3: 64.0,
        4: 48.0,
        7: 3.0,
    }

    def __init__(self, total_frames=3):
        self._remaining = total_frames

    def get(self, prop):
        return self._PROPS[prop]

    def read(self):
        if self._remaining <= 0:
            return False, None
        self._remaining -= 1
        return True, np.zeros((48, 64, 3), dtype=np.uint8)

    def release(self):
        pass


class _FakeWriter:
    def __init__(self):
        self.frames = 0

    def write(self, frame):
        self.frames += 1

    def release(self):
        pass


def _patch_common(monkeypatch, writer):
    monkeypatch.setattr(subtitled.cv2, "VideoCapture", lambda path: _FakeCapture())
    monkeypatch.setattr(subtitled.cv2, "VideoWriter", lambda *a, **k: writer)
    monkeypatch.setattr(subtitled.cv2, "VideoWriter_fourcc", lambda *a: 0)
    monkeypatch.setattr(subtitled, "draw_subtitle", lambda frame, *a: frame)
    monkeypatch.setattr(subtitled, "draw_dynamic_subtitle", lambda frame, *a: frame)
    monkeypatch.setattr(subtitled, "get_words_at_time", lambda segments, t: "word")
    monkeypatch.setattr(subtitled, "get_subtitle_chunk_at_time", lambda segments, t, n: (["word"], 0))
    monkeypatch.setattr(subtitled.os, "unlink", lambda path: None)


def _segments():
    return [Segment(0.0, 2.0, "word", words=[])]


def test_renders_every_frame_and_merges_audio(monkeypatch, tmp_path):
    writer = _FakeWriter()
    _patch_common(monkeypatch, writer)
    out_path = str(tmp_path / "video_subtitled.mp4")

    def fake_merge(tmp_video, source, output):
        with open(output, "wb") as fh:
            fh.write(b"x" * 1024)
        return SimpleNamespace(returncode=0, stderr="")

    encode_calls = []
    monkeypatch.setattr(subtitled, "merge_full_audio", fake_merge)
    monkeypatch.setattr(
        subtitled, "encode_without_audio", lambda *a: encode_calls.append(a) or SimpleNamespace(returncode=0)
    )

    result = subtitled.render_subtitled_video("in.mp4", _segments(), out_path, with_audio=True)

    assert result == out_path
    assert writer.frames == 3
    assert encode_calls == []


def test_no_audio_uses_encode_without_audio(monkeypatch, tmp_path):
    writer = _FakeWriter()
    _patch_common(monkeypatch, writer)
    out_path = str(tmp_path / "video_subtitled.mp4")

    def fake_encode(tmp_video, output):
        with open(output, "wb") as fh:
            fh.write(b"x" * 1024)
        return SimpleNamespace(returncode=0, stderr="")

    merge_calls = []
    monkeypatch.setattr(subtitled, "encode_without_audio", fake_encode)
    monkeypatch.setattr(
        subtitled, "merge_full_audio", lambda *a: merge_calls.append(a) or SimpleNamespace(returncode=0)
    )

    result = subtitled.render_subtitled_video("in.mp4", _segments(), out_path, with_audio=False)

    assert result == out_path
    assert merge_calls == []


def test_dynamic_subtitles_path(monkeypatch, tmp_path):
    writer = _FakeWriter()
    _patch_common(monkeypatch, writer)
    out_path = str(tmp_path / "video_subtitled.mp4")
    chunk_calls = []
    monkeypatch.setattr(
        subtitled,
        "get_subtitle_chunk_at_time",
        lambda segments, t, n: chunk_calls.append(t) or (["word"], 0),
    )

    def fake_merge(tmp_video, source, output):
        with open(output, "wb") as fh:
            fh.write(b"x")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(subtitled, "merge_full_audio", fake_merge)

    subtitled.render_subtitled_video("in.mp4", _segments(), out_path, with_audio=True, dynamic_subtitles=True)

    assert len(chunk_calls) == 3


def test_ffmpeg_failure_returns_none(monkeypatch, tmp_path):
    writer = _FakeWriter()
    _patch_common(monkeypatch, writer)
    out_path = str(tmp_path / "video_subtitled.mp4")
    monkeypatch.setattr(subtitled, "merge_full_audio", lambda *a: SimpleNamespace(returncode=1, stderr="boom"))

    result = subtitled.render_subtitled_video("in.mp4", _segments(), out_path, with_audio=True)

    assert result is None
