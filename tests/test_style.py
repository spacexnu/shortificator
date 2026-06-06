import pytest

from shortificator.subtitles.style import (
    DEFAULT_DYNAMIC_SUBTITLE_STYLE,
    DynamicSubtitleStyle,
    parse_color,
)


class TestParseColor:
    def test_rgb_triplet(self):
        assert parse_color("255,224,64") == (255, 224, 64)

    def test_rgb_with_whitespace(self):
        assert parse_color("  10,20,30  ") == (10, 20, 30)

    def test_hex(self):
        assert parse_color("#FFE040") == (255, 224, 64)

    def test_hex_lowercase(self):
        assert parse_color("#ffe040") == (255, 224, 64)

    @pytest.mark.parametrize("value", ["#FFF", "#GGGGGG", "1,2", "1,2,3,4", "300,0,0", "-1,0,0"])
    def test_invalid_raises(self, value):
        with pytest.raises(ValueError):
            parse_color(value)


class TestDynamicSubtitleStyle:
    def test_default_instance_matches_constant(self):
        assert DynamicSubtitleStyle() == DEFAULT_DYNAMIC_SUBTITLE_STYLE

    def test_documented_defaults(self):
        style = DynamicSubtitleStyle()
        assert style.words_per_chunk == 4
        assert style.uppercase is True
        assert style.color == (255, 255, 255)
        assert style.highlight_color == (255, 224, 64)
