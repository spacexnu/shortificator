import subprocess
from types import SimpleNamespace

from shortificator import media


class TestHasAudioStream:
    def test_true_when_ffprobe_reports_stream(self, monkeypatch):
        captured = {}

        def fake_run(cmd, capture_output, text):
            captured["cmd"] = cmd
            return SimpleNamespace(stdout="0\n", returncode=0)

        monkeypatch.setattr(media.subprocess, "run", fake_run)
        assert media.has_audio_stream("video.mp4") is True
        assert captured["cmd"][0] == "ffprobe"
        assert "video.mp4" in captured["cmd"]

    def test_false_when_no_stream(self, monkeypatch):
        monkeypatch.setattr(media.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="  \n", returncode=0))
        assert media.has_audio_stream("video.mp4") is False

    def test_missing_ffprobe_warns_and_assumes_audio(self, monkeypatch, capsys):
        def boom(*a, **k):
            raise FileNotFoundError

        monkeypatch.setattr(media.subprocess, "run", boom)
        assert media.has_audio_stream("video.mp4") is True
        assert "ffprobe not found" in capsys.readouterr().out


class TestFfmpegCommands:
    def _capture(self, monkeypatch):
        calls = {}

        def fake_run(cmd, capture_output, text):
            calls["cmd"] = cmd
            return SimpleNamespace(returncode=0, stderr="")

        monkeypatch.setattr(media.subprocess, "run", fake_run)
        return calls

    def test_merge_with_audio_command(self, monkeypatch):
        calls = self._capture(monkeypatch)
        media.merge_with_audio("tmp.mp4", "src.mp4", 10.0, 45.0, "out.mp4")
        cmd = calls["cmd"]
        assert cmd[0] == "ffmpeg"
        assert cmd[-1] == "out.mp4"
        assert "-map" in cmd and "0:v:0" in cmd and "1:a:0" in cmd
        assert cmd[cmd.index("-ss") + 1] == "10.0"
        assert cmd[cmd.index("-to") + 1] == "45.0"
        assert "aac" in cmd and "192k" in cmd

    def test_merge_full_audio_copies_audio_stream(self, monkeypatch):
        calls = []

        def fake_run(cmd, capture_output, text):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stderr="")

        monkeypatch.setattr(media.subprocess, "run", fake_run)
        media.merge_full_audio("tmp.mp4", "src.mp4", "out.mp4")
        assert len(calls) == 1
        cmd = calls[0]
        assert cmd[0] == "ffmpeg"
        assert cmd[-1] == "out.mp4"
        assert "-map" in cmd and "0:v:0" in cmd and "1:a:0" in cmd
        assert "-ss" not in cmd and "-to" not in cmd
        assert cmd[cmd.index("-c:a") + 1] == "copy"
        assert "aac" not in cmd

    def test_merge_full_audio_falls_back_to_aac(self, monkeypatch, capsys):
        calls = []

        def fake_run(cmd, capture_output, text):
            calls.append(cmd)
            returncode = 1 if len(calls) == 1 else 0
            return SimpleNamespace(returncode=returncode, stderr="could not find tag for codec")

        monkeypatch.setattr(media.subprocess, "run", fake_run)
        result = media.merge_full_audio("tmp.mp4", "src.mp4", "out.mp4")
        assert result.returncode == 0
        assert len(calls) == 2
        assert "aac" in calls[1] and "192k" in calls[1]
        assert "re-encoding audio as AAC" in capsys.readouterr().out

    def test_encode_without_audio_command(self, monkeypatch):
        calls = self._capture(monkeypatch)
        media.encode_without_audio("tmp.mp4", "out.mp4")
        cmd = calls["cmd"]
        assert cmd[0] == "ffmpeg"
        assert "-an" in cmd
        assert "1:a:0" not in cmd
        assert cmd[-1] == "out.mp4"

    def test_returns_completed_process(self, monkeypatch):
        monkeypatch.setattr(
            media.subprocess,
            "run",
            lambda *a, **k: subprocess.CompletedProcess(args=a[0], returncode=0, stderr=""),
        )
        result = media.encode_without_audio("tmp.mp4", "out.mp4")
        assert result.returncode == 0
