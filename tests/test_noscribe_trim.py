"""Tests for the audio pre-trim fallback paths (no `av` needed).

The happy path (actual trimming) requires the engine venv's `av` and is
verified manually; here we only guard the graceful-fallback behaviour that runs
in any environment.
"""
import sys
from pathlib import Path

from talktrace_ai.utils import noscribe_engine as ne
from talktrace_ai.utils import _audio_trim


def test_pretrim_returns_none_without_interpreter(tmp_path):
    # A non-existent venv interpreter must yield None (so run_transcription
    # falls back to noScribe's own --start/--stop), not raise.
    result = ne._pretrim_audio(tmp_path / "nope.exe", tmp_path / "a.wav", 1000, 2000)
    assert result is None


def test_audio_trim_main_rejects_bad_args(monkeypatch):
    # Wrong arg count -> usage error (2); importing the module must not need av.
    monkeypatch.setattr(sys, "argv", ["_audio_trim.py"])
    assert _audio_trim.main() == 2
    # Non-integer bounds -> 2 as well.
    monkeypatch.setattr(sys, "argv", ["_audio_trim.py", "a.wav", "b.wav", "x", "y"])
    assert _audio_trim.main() == 2
