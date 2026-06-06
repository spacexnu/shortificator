from shortificator.models import Segment
from shortificator.subtitles.srt import build_srt, format_timestamp


class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0) == "00:00:00,000"

    def test_milliseconds(self):
        assert format_timestamp(1.234) == "00:00:01,234"

    def test_hours_minutes_seconds(self):
        assert format_timestamp(3661.5) == "01:01:01,500"

    def test_negative_clamped(self):
        assert format_timestamp(-5) == "00:00:00,000"

    def test_no_millisecond_overflow(self):
        assert format_timestamp(0.9999) == "00:00:01,000"


class TestBuildSrt:
    def _segments(self):
        return [
            Segment(0.0, 2.0, "primeiro"),
            Segment(2.0, 4.0, "segundo"),
            Segment(10.0, 12.0, "fora da janela"),
        ]

    def test_offsets_to_clip_start(self):
        srt = build_srt(self._segments(), start=2.0, end=4.0)
        assert srt == "1\n00:00:00,000 --> 00:00:02,000\nsegundo\n"

    def test_includes_all_overlapping_segments(self):
        srt = build_srt(self._segments(), start=0.0, end=4.0)
        assert "1\n00:00:00,000 --> 00:00:02,000\nprimeiro" in srt
        assert "2\n00:00:02,000 --> 00:00:04,000\nsegundo" in srt
        assert "fora da janela" not in srt

    def test_clamps_partial_overlap_to_window(self):
        segs = [Segment(1.0, 6.0, "atravessa")]
        srt = build_srt(segs, start=2.0, end=5.0)
        # clamped to [2,5] then offset by -2 → [0,3]
        assert srt == "1\n00:00:00,000 --> 00:00:03,000\natravessa\n"

    def test_skips_empty_text(self):
        segs = [Segment(0.0, 2.0, "   "), Segment(2.0, 4.0, "ok")]
        srt = build_srt(segs, start=0.0, end=4.0)
        assert "ok" in srt
        assert srt.startswith("1\n")  # the blank segment did not get a number

    def test_no_overlap_returns_empty(self):
        assert build_srt(self._segments(), start=20.0, end=30.0) == ""

    def test_end_none_keeps_everything_from_start(self):
        srt = build_srt(self._segments(), start=0.0)
        assert "fora da janela" in srt
