from shortificator.models import Segment
from shortificator.subtitles import timing


class TestGetWordsAtTime:
    def test_returns_joined_string(self, segments):
        assert timing.get_words_at_time(segments, 1.0) == "o gato subiu"

    def test_outside_any_segment_is_empty(self, segments):
        assert timing.get_words_at_time(segments, 4.0) == ""


class TestGetSubtitleWordsAtTime:
    def test_active_word_index(self, segments):
        words, idx = timing.get_subtitle_words_at_time(segments, 1.0)
        assert words == ["o", "gato", "subiu"]
        assert idx == 1

    def test_segment_without_words_falls_back_to_text(self):
        seg = [Segment(0.0, 2.0, "texto sem palavras")]
        words, idx = timing.get_subtitle_words_at_time(seg, 1.0)
        assert words == ["texto", "sem", "palavras"]
        assert idx is None

    def test_gap_returns_empty(self, segments):
        assert timing.get_subtitle_words_at_time(segments, 4.0) == ([], None)


class TestGetSubtitleChunkAtTime:
    def test_static_block_and_highlight(self, segments):
        block, active = timing.get_subtitle_chunk_at_time(segments, 1.0, chunk_size=2)
        assert block == ["o", "gato"]
        assert active == 1

    def test_block_advances_with_speech(self, segments):
        block, active = timing.get_subtitle_chunk_at_time(segments, 2.0, chunk_size=2)
        assert block == ["subiu"]
        assert active == 0

    def test_micro_pause_holds_last_block_without_highlight(self):
        seg = [
            Segment(
                0.0,
                10.0,
                "um dois tres",
                words=[
                    {"word": "um", "start": 0.0, "end": 1.0},
                    {"word": "dois", "start": 1.0, "end": 2.0},
                    {"word": "tres", "start": 5.0, "end": 6.0},
                ],
            )
        ]
        # t=3.5 is between word 2 and word 3: hold the block, no active word.
        block, active = timing.get_subtitle_chunk_at_time(seg, 3.5, chunk_size=2)
        assert active is None
        assert block  # something is still shown (held)

    def test_before_any_segment_is_empty(self, segments):
        assert timing.get_subtitle_chunk_at_time(segments, -1.0, chunk_size=2) == ([], None)

    def test_chunk_size_floor_of_one(self, segments):
        block, _ = timing.get_subtitle_chunk_at_time(segments, 0.6, chunk_size=0)
        assert len(block) == 1
