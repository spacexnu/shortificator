import json

import pytest

from shortificator import pipeline
from shortificator.models import Segment, ShortCandidate


@pytest.fixture
def patched(monkeypatch):
    """Stub the heavy stages so run() can be exercised in isolation."""
    calls = {"transcribe": 0, "analyze": 0, "render": []}

    def fake_transcribe(path):
        calls["transcribe"] += 1
        return [Segment(0.0, 60.0, "texto", words=[])]

    def fake_analyze(segments, **kwargs):
        calls["analyze"] += 1
        return [ShortCandidate(10.0, 45.0, "hook", "reason", 9)]

    def fake_render(input_video, candidate, segments, out_path, index, **kwargs):
        calls["render"].append(out_path)
        return out_path

    monkeypatch.setattr(pipeline, "has_audio_stream", lambda path: True)
    monkeypatch.setattr(pipeline, "transcribe", fake_transcribe)
    monkeypatch.setattr(pipeline, "analyze_with_llm", fake_analyze)
    monkeypatch.setattr(pipeline, "render_short", fake_render)
    return calls


def test_full_flow_transcribes_analyzes_and_renders(patched, tmp_path):
    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=1)

    assert patched["transcribe"] == 1
    assert patched["analyze"] == 1
    assert len(patched["render"]) == 1

    assert (tmp_path / "my_video_transcript.json").exists()
    candidates_file = tmp_path / "my_video_candidates.json"
    assert candidates_file.exists()
    data = json.loads(candidates_file.read_text())
    assert data[0]["hook"] == "hook"


def test_reuses_transcript_and_skips_whisper(patched, tmp_path):
    transcript = tmp_path / "prev_transcript.json"
    transcript.write_text(
        json.dumps([{"start": 0.0, "end": 30.0, "text": "oi", "words": []}]),
        encoding="utf-8",
    )

    pipeline.run(
        input_video="my_video.mp4",
        output_dir=str(tmp_path),
        transcript_json=str(transcript),
        max_shorts=1,
    )

    assert patched["transcribe"] == 0
    assert patched["analyze"] == 1


def test_reuses_candidates_and_skips_llm(patched, tmp_path):
    candidates = tmp_path / "prev_candidates.json"
    candidates.write_text(
        json.dumps([{"start": 5.0, "end": 40.0, "hook": "h", "reason": "r", "score": 7}]),
        encoding="utf-8",
    )

    pipeline.run(
        input_video="my_video.mp4",
        output_dir=str(tmp_path),
        candidates_json=str(candidates),
        max_shorts=1,
    )

    assert patched["analyze"] == 0
    assert len(patched["render"]) == 1


def test_no_candidates_aborts_before_render(patched, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(pipeline, "analyze_with_llm", lambda segments, **kw: [])
    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=1)

    assert patched["render"] == []
    assert "No candidates found" in capsys.readouterr().out


def test_max_shorts_limits_render_count(patched, monkeypatch, tmp_path):
    many = [ShortCandidate(s * 60.0, s * 60.0 + 40.0, "h", "r", 9) for s in range(5)]
    monkeypatch.setattr(pipeline, "analyze_with_llm", lambda segments, **kw: many)

    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=2)
    assert len(patched["render"]) == 2


def test_warns_when_no_audio(patched, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(pipeline, "has_audio_stream", lambda path: False)
    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=1)
    assert "no audio stream" in capsys.readouterr().out


def test_srt_written_next_to_short_when_enabled(patched, tmp_path):
    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=1, generate_srt=True)
    srt = tmp_path / "my_video_short_01.srt"
    assert srt.exists()
    assert "-->" in srt.read_text(encoding="utf-8")


def test_full_video_srt_written_when_enabled(patched, tmp_path):
    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=1, generate_srt=True)
    full_srt = tmp_path / "my_video.srt"
    assert full_srt.exists()
    assert "-->" in full_srt.read_text(encoding="utf-8")


def test_srt_not_written_by_default(patched, tmp_path):
    pipeline.run(input_video="my_video.mp4", output_dir=str(tmp_path), max_shorts=1)
    assert not (tmp_path / "my_video_short_01.srt").exists()
    assert not (tmp_path / "my_video.srt").exists()


def test_duration_bounds_forwarded_to_analysis(patched, monkeypatch, tmp_path):
    received = {}

    def fake_analyze(segments, **kwargs):
        received.update(kwargs)
        return [ShortCandidate(10.0, 30.0, "h", "r", 9)]

    monkeypatch.setattr(pipeline, "analyze_with_llm", fake_analyze)
    pipeline.run(
        input_video="my_video.mp4",
        output_dir=str(tmp_path),
        max_shorts=1,
        min_duration=15,
        max_duration=40,
    )
    assert received["min_secs"] == 15
    assert received["max_secs"] == 40
