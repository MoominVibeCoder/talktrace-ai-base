"""Tests for transcript format detection + noScribe→standard conversion."""
from talktrace_ai.utils.transcript_format import (
    is_valid_transcript_format,
    convert_to_standard_format,
)


# --- is_valid_transcript_format --------------------------------------

def test_valid_standard_format():
    assert is_valid_transcript_format("S01: Hallo\nS02: Hi") is True


def test_empty_is_invalid():
    assert is_valid_transcript_format("") is False
    assert is_valid_transcript_format(None) is False


def test_speaker_header_lines_are_invalid():
    # A bare "SPEAKER_00:" header line means it's still in noScribe format.
    text = "SPEAKER_00:\nHallo zusammen"
    assert is_valid_transcript_format(text) is False


def test_teacher_label_counts_as_valid():
    text = "Lehrkraft: Guten Morgen\nS01: Morgen"
    assert is_valid_transcript_format(text, teacher="Lehrkraft") is True


def test_prose_without_speakers_is_invalid():
    assert is_valid_transcript_format("Just some prose, no speakers here.") is False


# --- convert_to_standard_format --------------------------------------

def test_convert_basic_noscribe():
    src = "SPEAKER_00:\nHallo\nSPEAKER_01:\nWelt"
    assert convert_to_standard_format(src) == "S00: Hallo\nS01: Welt"


def test_convert_renumbers_by_speaker_id():
    # Speaker ids are kept as their numeric value, zero-padded to two digits.
    src = "SPEAKER_02:\neins\nSPEAKER_05:\nzwei"
    assert convert_to_standard_format(src) == "S02: eins\nS05: zwei"


def test_convert_joins_multiline_body_and_collapses_whitespace():
    src = "SPEAKER_00:\nerste   Zeile\nzweite Zeile"
    assert convert_to_standard_format(src) == "S00: erste Zeile zweite Zeile"


def test_convert_skips_preamble_before_first_speaker():
    src = "irgendein Vorspann\nSPEAKER_00:\nText"
    assert convert_to_standard_format(src) == "S00: Text"


def test_convert_empty():
    assert convert_to_standard_format("") == ""
