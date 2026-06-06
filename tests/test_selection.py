import pytest

from shortificator.analysis import selection
from shortificator.config import SHORT_MAX_SECS, SHORT_MIN_SECS
from shortificator.models import Segment, ShortCandidate


def _candidate(start: float, end: float, score: int = 5) -> ShortCandidate:
    return ShortCandidate(start=start, end=end, hook="h", reason="r", score=score)


class TestBuildTranscriptText:
    def test_includes_timestamps_and_text(self):
        segments = [Segment(0.0, 1.5, "ola"), Segment(2.0, 4.25, "mundo")]
        out = selection.build_transcript_text(segments)
        assert out == "[0.0s - 1.5s] ola\n[2.0s - 4.2s] mundo"

    def test_empty(self):
        assert selection.build_transcript_text([]) == ""


class TestHasCjk:
    # The guard targets ideographic ranges (its real concern is Chinese output);
    # Latin, accents, kana and punctuation are intentionally not flagged.
    @pytest.mark.parametrize("text", ["hello", "ção é ótimo", "123 !@#", "", "テスト", "あ"])
    def test_non_cjk(self, text):
        assert selection.has_cjk(text) is False

    @pytest.mark.parametrize("text", ["你好", "mix 世界 mix"])
    def test_cjk(self, text):
        assert selection.has_cjk(text) is True


class TestOverlapRatio:
    def test_disjoint(self):
        assert selection.overlap_ratio(_candidate(0, 10), _candidate(20, 30)) == 0.0

    def test_full_containment_is_one(self):
        # shorter clip fully inside the longer one
        assert selection.overlap_ratio(_candidate(0, 100), _candidate(10, 20)) == 1.0

    def test_partial(self):
        ratio = selection.overlap_ratio(_candidate(0, 10), _candidate(5, 15))
        assert ratio == pytest.approx(0.5)


class TestDedupe:
    def test_drops_high_overlap(self):
        cands = [_candidate(0, 10), _candidate(1, 11), _candidate(50, 60)]
        kept = selection.dedupe_overlapping_candidates(cands, max_candidates=5)
        assert [(c.start, c.end) for c in kept] == [(0, 10), (50, 60)]

    def test_respects_max_candidates(self):
        cands = [_candidate(0, 10), _candidate(50, 60), _candidate(100, 110)]
        kept = selection.dedupe_overlapping_candidates(cands, max_candidates=2)
        assert len(kept) == 2

    def test_keeps_when_below_threshold(self):
        cands = [_candidate(0, 10), _candidate(8, 18)]  # 2s/10s = 0.2 overlap
        kept = selection.dedupe_overlapping_candidates(cands, max_candidates=5)
        assert len(kept) == 2


class TestPlanWindows:
    def test_single_window_for_one_candidate(self):
        assert selection.plan_windows(600, 1) == [(0.0, 600.0)]

    def test_single_window_for_zero_duration(self):
        assert selection.plan_windows(0, 5) == [(0.0, 0.0)]

    def test_splits_into_contiguous_windows(self):
        windows = selection.plan_windows(600, 3)
        assert windows == [(0.0, 200.0), (200.0, 400.0), (400.0, 600.0)]

    def test_last_window_ends_exactly_at_video_end(self):
        windows = selection.plan_windows(933.5, 4)
        assert windows[0][0] == 0.0
        assert windows[-1][1] == pytest.approx(933.5)
        # windows are contiguous: each start equals the previous end
        for prev, nxt in zip(windows, windows[1:], strict=False):
            assert prev[1] == pytest.approx(nxt[0])


class TestTimeWindowGuidance:
    def test_single_candidate(self):
        assert "Single candidate run" in selection.build_time_window_guidance(600, 1)

    def test_zero_video_end(self):
        assert "Single candidate run" in selection.build_time_window_guidance(0, 5)

    def test_splits_into_windows(self):
        out = selection.build_time_window_guidance(600, 3).splitlines()
        assert len(out) == 3
        assert "between 0s and 200s" in out[0]
        assert "between 400s and 600s" in out[2]


class TestFitClipWindow:
    def test_short_clip_grows_to_minimum(self):
        start, end = selection.fit_clip_window(100, 110, 600)
        assert end - start == pytest.approx(SHORT_MIN_SECS)

    def test_long_clip_trimmed_to_maximum(self):
        start, end = selection.fit_clip_window(10, 400, 600)
        assert end - start == pytest.approx(SHORT_MAX_SECS)

    def test_in_range_clip_preserved(self):
        start, end = selection.fit_clip_window(10, 50, 600)
        assert (start, end) == (10, 50)

    def test_video_too_short_returns_none(self):
        assert selection.fit_clip_window(0, 5, 10) == (None, None)

    def test_clamped_to_video_bounds(self):
        start, end = selection.fit_clip_window(590, 600, 600)
        assert end <= 600
        assert start >= 0
        assert end - start == pytest.approx(SHORT_MIN_SECS)

    def test_result_is_rounded(self):
        start, end = selection.fit_clip_window(10.123456, 50.987654, 600)
        assert start == round(start, 2)
        assert end == round(end, 2)

    def test_custom_bounds_grow_to_custom_minimum(self):
        start, end = selection.fit_clip_window(100, 105, 600, min_secs=45, max_secs=90)
        assert end - start == pytest.approx(45)

    def test_custom_bounds_trim_to_custom_maximum(self):
        start, end = selection.fit_clip_window(10, 400, 600, min_secs=45, max_secs=90)
        assert end - start == pytest.approx(90)
