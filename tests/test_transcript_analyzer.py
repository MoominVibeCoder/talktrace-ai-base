"""Tests for the multi-stage transcript converter (pure)."""
from talktrace_ai.transcript_analyzer import (
    analyze_transcript,
    suggest_default_options,
    convert_with_options,
    ConversionOptions,
)


NOSCRIBE = (
    "00:00:01\n"
    "SPEAKER_00:\n"
    "Guten Morgen [lacht]\n"
    "SPEAKER_01:\n"
    "Morgen!\n"
)


# --- analyze_transcript ----------------------------------------------

def test_analyze_empty_returns_blank_analysis():
    a = analyze_transcript("")
    assert a.speakers == []
    assert a.speaker_format == "unknown"
    assert a.line_count == 0


def test_analyze_detects_noscribe_speakers_in_order():
    a = analyze_transcript(NOSCRIBE)
    assert a.speakers == ["SPEAKER_00", "SPEAKER_01"]
    assert a.speaker_format == "noScribe"


def test_analyze_detects_timestamps_and_brackets():
    a = analyze_transcript(NOSCRIBE)
    assert a.timestamp_patterns, "expected a timestamp sample"
    assert any(g.delimiter == "[]" for g in a.bracket_patterns)


def test_analyze_detects_inline_speakers():
    a = analyze_transcript("Anna: hallo\nBen: hi")
    assert a.speaker_format == "inline"
    assert a.speakers == ["Anna", "Ben"]


# --- suggest_default_options -----------------------------------------

def test_suggest_maps_teacher_hint_to_TEACHER():
    a = analyze_transcript("Lehrer: Guten Morgen\nSPEAKER_01:\nHi")
    opts = suggest_default_options(a, teacher_hint="Lehrer")
    assert opts.speaker_map.get("Lehrer") == "TEACHER"


def test_suggest_numbers_remaining_speakers():
    a = analyze_transcript(NOSCRIBE)
    opts = suggest_default_options(a, teacher_hint=None)
    # No teacher match → both become S01/S02 in order of appearance.
    assert opts.speaker_map == {"SPEAKER_00": "S01", "SPEAKER_01": "S02"}


# --- convert_with_options --------------------------------------------

def test_convert_full_pipeline_strips_timestamps_and_brackets():
    a = analyze_transcript(NOSCRIBE)
    opts = suggest_default_options(a, teacher_hint=None)
    out = convert_with_options(NOSCRIBE, opts)
    lines = out.splitlines()
    assert lines == ["S01: Guten Morgen", "S02: Morgen!"]
    assert "[lacht]" not in out  # [] stripped by default
    assert "00:00:01" not in out  # timestamp stripped


def test_convert_teacher_label_applied():
    src = "SPEAKER_00:\nFrage?\nSPEAKER_01:\nAntwort"
    opts = ConversionOptions(
        speaker_map={"SPEAKER_00": "TEACHER", "SPEAKER_01": "S01"},
        teacher_label="Lehrkraft",
    )
    out = convert_with_options(src, opts)
    assert out == "Lehrkraft: Frage?\nS01: Antwort"


def test_convert_none_mapping_drops_speaker():
    src = "SPEAKER_00:\nbehalten\nSPEAKER_01:\nweg"
    opts = ConversionOptions(speaker_map={"SPEAKER_00": "S01", "SPEAKER_01": None})
    out = convert_with_options(src, opts)
    assert out == "S01: behalten"


def test_convert_empty():
    assert convert_with_options("", ConversionOptions()) == ""
