import json
import re
import sys
from types import SimpleNamespace

import pytest

from shortificator.analysis import llm
from shortificator.config import SHORT_MIN_SECS
from shortificator.models import Segment


@pytest.fixture
def transcript_segments():
    return [Segment(start=0.0, end=120.0, text="conteudo longo o suficiente", words=[])]


def _install_fake_ollama(monkeypatch, content="", raises=None):
    captured = {}

    def chat(**kwargs):
        captured.update(kwargs)
        if raises is not None:
            raise raises
        return {"message": {"content": content}}

    monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(chat=chat))
    return captured


class TestBuildAnalysisSchema:
    def test_structure(self):
        schema = llm.build_analysis_schema(5)
        items = schema["properties"]["candidates"]["items"]
        assert set(items["required"]) == {"start", "end", "hook", "reason", "score"}
        assert schema["properties"]["candidates"]["maxItems"] == 5

    def test_max_items_floor_of_one(self):
        assert llm.build_analysis_schema(0)["properties"]["candidates"]["maxItems"] == 1


class TestAnalyzeWithLlm:
    def test_parses_and_fits_candidates(self, monkeypatch, transcript_segments):
        payload = json.dumps(
            {
                "candidates": [
                    {"start": 10, "end": 14, "hook": "h1", "reason": "r1", "score": 8},
                    {"start": 70, "end": 80, "hook": "h2", "reason": "r2", "score": 9},
                ]
            }
        )
        captured = _install_fake_ollama(monkeypatch, content=payload)

        result = llm.analyze_with_llm(transcript_segments, model="m", max_candidates=5)

        assert len(result) == 2
        # sorted by score desc
        assert result[0].score == 9
        # short clip (10..14) was grown to the minimum window
        grown = next(c for c in result if c.hook == "h1")
        assert grown.end - grown.start >= SHORT_MIN_SECS
        assert captured["model"] == "m"
        assert "format" in captured

    def test_custom_duration_bounds_are_honored(self, monkeypatch, transcript_segments):
        payload = json.dumps({"candidates": [{"start": 10, "end": 12, "hook": "h", "reason": "r", "score": 5}]})
        _install_fake_ollama(monkeypatch, content=payload)
        result = llm.analyze_with_llm(transcript_segments, max_candidates=1, min_secs=20, max_secs=25)
        assert len(result) == 1
        assert result[0].end - result[0].start == pytest.approx(20)

    def test_json_wrapped_in_prose_is_extracted(self, monkeypatch, transcript_segments):
        payload = 'sure! here you go:\n{"candidates": [{"start": 10, "end": 50, "hook": "h", "reason": "r", "score": 5}]}\nthanks'
        _install_fake_ollama(monkeypatch, content=payload)
        result = llm.analyze_with_llm(transcript_segments, max_candidates=1)
        assert len(result) == 1

    def test_no_json_returns_empty(self, monkeypatch, transcript_segments, capsys):
        _install_fake_ollama(monkeypatch, content="no json at all")
        assert llm.analyze_with_llm(transcript_segments) == []
        assert "did not return valid JSON" in capsys.readouterr().out

    def test_malformed_json_returns_empty(self, monkeypatch, transcript_segments, capsys):
        _install_fake_ollama(monkeypatch, content='{"candidates": [bad json}')
        assert llm.analyze_with_llm(transcript_segments) == []
        assert "Malformed LLM JSON" in capsys.readouterr().out

    def test_ollama_failure_returns_empty(self, monkeypatch, transcript_segments, capsys):
        _install_fake_ollama(monkeypatch, raises=RuntimeError("connection refused"))
        assert llm.analyze_with_llm(transcript_segments) == []
        assert "Failed to call Ollama" in capsys.readouterr().out

    def test_overlapping_candidates_deduped(self, monkeypatch, transcript_segments, capsys):
        payload = json.dumps(
            {
                "candidates": [
                    {"start": 10, "end": 50, "hook": "a", "reason": "r", "score": 9},
                    {"start": 11, "end": 51, "hook": "b", "reason": "r", "score": 8},
                ]
            }
        )
        _install_fake_ollama(monkeypatch, content=payload)
        result = llm.analyze_with_llm(transcript_segments, max_candidates=5)
        assert len(result) == 1
        assert "overlapping duplicate" in capsys.readouterr().out

    def test_windowing_queries_each_region(self, monkeypatch):
        # 10 segments evenly spread across ~365s of video.
        segs = [Segment(start=float(i * 40), end=float(i * 40 + 5), text=f"m{i}", words=[]) for i in range(10)]
        calls = {"n": 0}

        def chat(**kwargs):
            calls["n"] += 1
            user = kwargs["messages"][-1]["content"]
            # Return a candidate anchored to the first timestamp of the window's transcript.
            start = float(re.search(r"\[(\d+\.\d+)s", user).group(1))
            payload = json.dumps(
                {"candidates": [{"start": start, "end": start + 40, "hook": f"h{start}", "reason": "r", "score": 5}]}
            )
            return {"message": {"content": payload}}

        monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(chat=chat))
        result = llm.analyze_with_llm(segs, max_candidates=4)

        assert calls["n"] == 4  # one request per time window
        assert len(result) >= 3
        starts = sorted(c.start for c in result)
        assert starts[0] < starts[-1]  # candidates span different regions

    def test_empty_segments_returns_empty(self, monkeypatch, capsys):
        _install_fake_ollama(monkeypatch, content="{}")
        assert llm.analyze_with_llm([]) == []
        assert "0 valid candidates found" in capsys.readouterr().out

    def test_cjk_warning(self, monkeypatch, transcript_segments, capsys):
        payload = json.dumps({"candidates": [{"start": 10, "end": 50, "hook": "你好", "reason": "r", "score": 5}]})
        _install_fake_ollama(monkeypatch, content=payload)
        llm.analyze_with_llm(transcript_segments)
        assert "Chinese (CJK)" in capsys.readouterr().out
