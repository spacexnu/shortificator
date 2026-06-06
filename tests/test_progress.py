from shortificator import progress


class TestFormatDuration:
    def test_seconds(self):
        assert progress.format_duration(45) == "45s"

    def test_minutes(self):
        assert progress.format_duration(125) == "2m05s"

    def test_hours(self):
        assert progress.format_duration(3725) == "1h02m"

    def test_negative_clamped_to_zero(self):
        assert progress.format_duration(-10) == "0s"


class TestPrintProgressBar:
    def test_zero_total_prints_nothing(self, capsys):
        progress.print_progress_bar("Frames", 0, 0, 0.0)
        assert capsys.readouterr().out == ""

    def test_finish_done(self, capsys):
        progress.print_progress_bar("Frames", 10, 10, 0.0, finish=True)
        out = capsys.readouterr().out
        assert "done" in out
        assert "100.0%" in out
        assert out.endswith("\n")

    def test_finish_stopped_when_incomplete(self, capsys):
        progress.print_progress_bar("Frames", 5, 10, 0.0, finish=True)
        assert "stopped" in capsys.readouterr().out

    def test_in_progress_uses_carriage_return(self, capsys):
        progress.print_progress_bar("Frames", 5, 10, 0.0)
        out = capsys.readouterr().out
        assert "ETA" in out
        assert out.endswith("\r")
