import pytest

from shortificator import cli


def parse(args: list[str]):
    return cli.build_parser().parse_args(args)


class TestParserDefaults:
    def test_core_defaults(self):
        ns = parse(["--input", "v.mp4"])
        assert ns.input == "v.mp4"
        assert ns.output == "./shorts_output"
        assert ns.model == "llama3"
        assert ns.max_shorts == 5
        assert ns.crop_mode == "face"
        assert ns.content_mode == "talking-head"
        assert ns.dynamic_subtitles is False

    def test_short_flags(self):
        ns = parse(["-i", "v.mp4", "-o", "out", "-m", "mistral-small", "-n", "3"])
        assert (ns.output, ns.model, ns.max_shorts) == ("out", "mistral-small", 3)

    @pytest.mark.parametrize("mode", ["face", "center", "gameplay", "auto"])
    def test_crop_mode_choices(self, mode):
        assert parse(["-i", "v.mp4", "--crop-mode", mode]).crop_mode == mode

    def test_invalid_crop_mode_rejected(self):
        with pytest.raises(SystemExit):
            parse(["-i", "v.mp4", "--crop-mode", "nope"])

    def test_duration_defaults(self):
        ns = parse(["-i", "v.mp4"])
        assert ns.min_duration == 30
        assert ns.max_duration == 60

    def test_duration_overrides(self):
        ns = parse(["-i", "v.mp4", "--min-duration", "20", "--max-duration", "45"])
        assert ns.min_duration == 20
        assert ns.max_duration == 45

    def test_clip_defaults_to_none(self):
        assert parse(["-i", "v.mp4"]).clip is None

    def test_clip_is_repeatable(self):
        ns = parse(["-i", "v.mp4", "--clip", "1:30-2:10", "--clip", "5:00-5:45"])
        assert ns.clip == ["1:30-2:10", "5:00-5:45"]


class TestParseTimestamp:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("90", 90.0),
            ("90.5", 90.5),
            ("1:30", 90.0),
            ("01:02:03", 3723.0),
            ("0:00:10.25", 10.25),
        ],
    )
    def test_valid_formats(self, value, expected):
        assert cli.parse_timestamp(value) == expected

    @pytest.mark.parametrize("value", ["", "abc", "1:2:3:4", "1:-5", "::"])
    def test_invalid_formats(self, value):
        with pytest.raises(ValueError):
            cli.parse_timestamp(value)


class TestParseClips:
    def test_multiple_clips(self):
        clips = cli.parse_clips(["1:30-2:10", "300-360.5"])
        assert clips == [(90.0, 130.0), (300.0, 360.5)]

    @pytest.mark.parametrize("spec", ["1:30", "1:30-", "-2:10", "2:10-1:30", "1:30-1:30"])
    def test_invalid_specs(self, spec):
        with pytest.raises(ValueError):
            cli.parse_clips([spec])


class TestBuildDynamicSubtitleStyle:
    def test_defaults_preserved_when_no_flags(self):
        style = cli.build_dynamic_subtitle_style(parse(["-i", "v.mp4"]))
        assert style.font_px == 78
        assert style.uppercase is True
        assert style.words_per_chunk == 4

    def test_flags_override(self):
        ns = parse(
            [
                "-i",
                "v.mp4",
                "--sub-font-size",
                "40",
                "--sub-color",
                "#000000",
                "--sub-highlight-color",
                "1,2,3",
                "--sub-words-per-chunk",
                "6",
                "--sub-no-uppercase",
                "--sub-y-ratio",
                "0.5",
                "--sub-max-lines",
                "3",
            ]
        )
        style = cli.build_dynamic_subtitle_style(ns)
        assert style.font_px == 40
        assert style.min_font_px == 40  # min(48, 40)
        assert style.color == (0, 0, 0)
        assert style.highlight_color == (1, 2, 3)
        assert style.words_per_chunk == 6
        assert style.uppercase is False
        assert style.y_ratio == 0.5
        assert style.max_lines == 3

    def test_invalid_color_exits(self):
        ns = parse(["-i", "v.mp4", "--sub-color", "300,0,0"])
        with pytest.raises(SystemExit):
            cli.build_dynamic_subtitle_style(ns)

    def test_negative_words_per_chunk_exits(self):
        ns = parse(["-i", "v.mp4", "--sub-words-per-chunk", "-1"])
        with pytest.raises(SystemExit):
            cli.build_dynamic_subtitle_style(ns)

    def test_zero_words_per_chunk_is_treated_as_unset(self):
        # 0 is falsy, so the override is skipped and the default is kept.
        ns = parse(["-i", "v.mp4", "--sub-words-per-chunk", "0"])
        style = cli.build_dynamic_subtitle_style(ns)
        assert style.words_per_chunk == 4

    def test_missing_font_exits(self, tmp_path):
        ns = parse(["-i", "v.mp4", "--sub-font", str(tmp_path / "nope.ttf")])
        with pytest.raises(SystemExit):
            cli.build_dynamic_subtitle_style(ns)


class TestMainValidation:
    def test_requires_an_input(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog"])
        with pytest.raises(SystemExit):
            cli.main()
        assert "Provide --input" in capsys.readouterr().out

    def test_rejects_both_inputs(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "-i", "v.mp4", "-u", "http://x"])
        with pytest.raises(SystemExit):
            cli.main()
        assert "not both" in capsys.readouterr().out

    def test_missing_input_file(self, monkeypatch, capsys, tmp_path):
        missing = str(tmp_path / "absent.mp4")
        monkeypatch.setattr("sys.argv", ["prog", "-i", missing])
        with pytest.raises(SystemExit):
            cli.main()
        assert "File not found" in capsys.readouterr().out

    def test_rejects_min_duration_below_one(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "-i", "v.mp4", "--min-duration", "0"])
        with pytest.raises(SystemExit):
            cli.main()
        assert "--min-duration must be >= 1" in capsys.readouterr().out

    def test_rejects_max_not_greater_than_min(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "-i", "v.mp4", "--min-duration", "40", "--max-duration", "40"])
        with pytest.raises(SystemExit):
            cli.main()
        assert "--max-duration must be greater" in capsys.readouterr().out

    def test_rejects_clip_with_candidates(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            ["prog", "-i", "v.mp4", "--clip", "1:30-2:10", "--candidates", "c.json"],
        )
        with pytest.raises(SystemExit):
            cli.main()
        assert "either --clip or --candidates" in capsys.readouterr().out

    def test_rejects_invalid_clip_spec(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "-i", "v.mp4", "--clip", "2:10-1:30"])
        with pytest.raises(SystemExit):
            cli.main()
        assert "end must be greater than start" in capsys.readouterr().out
