"""Tests for the deterministic quantitative stats helpers."""
from talktrace_ai.utils.stats import (
    count_pupils,
    _parse_turns,
    dialog_stats,
    dialog_stats_per_speaker,
    count_transcript_turns,
    count_teacher_impulses,
)


TEACHER = "Lehrkraft"
TRANSCRIPT = (
    "Lehrkraft: Guten Morgen, was fällt euch dazu ein?\n"
    "S01: Mir fällt etwas ein.\n"
    "S02: Mir auch.\n"
    "Lehrkraft: Schön.\n"
    "S01: Noch ein Beitrag hier.\n"
)


# --- count_pupils ----------------------------------------------------

def test_count_pupils_counts_distinct_students():
    assert count_pupils(TRANSCRIPT) == 2  # S01, S02


def test_count_pupils_zero_without_students():
    assert count_pupils("Lehrkraft: nur ich rede hier.") == 0


# --- _parse_turns ----------------------------------------------------

def test_parse_turns_order_and_count():
    turns = _parse_turns(TRANSCRIPT, TEACHER)
    assert len(turns) == 5
    assert turns[0] == ("Lehrkraft", "Guten Morgen, was fällt euch dazu ein?")
    assert [spk for spk, _ in turns] == [
        "Lehrkraft", "S01", "S02", "Lehrkraft", "S01"
    ]


def test_parse_turns_normalizes_teacher_case():
    turns = _parse_turns("lehrkraft: hallo\nS01: hi", TEACHER)
    assert turns[0][0] == "Lehrkraft"  # canonical casing applied


def test_count_transcript_turns():
    assert count_transcript_turns(TRANSCRIPT, TEACHER) == 5


# --- dialog_stats ----------------------------------------------------

def test_dialog_stats_splits_teacher_and_students():
    df = dialog_stats(TRANSCRIPT, TEACHER)
    speakers = set(df["Sprecher"])
    assert TEACHER in speakers
    assert "Schüler:innen" in speakers

    teacher_row = df[df["Sprecher"] == TEACHER].iloc[0]
    students_row = df[df["Sprecher"] == "Schüler:innen"].iloc[0]
    assert teacher_row["Anzahl_Beitraege"] == 2
    assert students_row["Anzahl_Beitraege"] == 3  # S01 ×2 + S02 ×1


def test_dialog_stats_per_speaker_keeps_each_student():
    df = dialog_stats_per_speaker(TRANSCRIPT, TEACHER)
    by = dict(zip(df["Sprecher"], df["Anzahl_Beitraege"]))
    assert by["Lehrkraft"] == 2
    assert by["S01"] == 2
    assert by["S02"] == 1


# --- count_teacher_impulses ------------------------------------------

def test_count_teacher_impulses():
    df = dialog_stats(TRANSCRIPT, TEACHER)
    assert count_teacher_impulses(df, TEACHER) == 2


def test_count_teacher_impulses_missing_returns_zero():
    df = dialog_stats(TRANSCRIPT, TEACHER)
    assert count_teacher_impulses(df, "NichtVorhanden") == 0
