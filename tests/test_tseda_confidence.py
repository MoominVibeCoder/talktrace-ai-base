"""Tests für die T-SEDA-Vorlage und die Konfidenz-Pipeline (Multi-Coding).

Deckt die pure Logik ab: Vorlagen-Inhalt (Codes, DE/EN, Auffang-Kategorie
zuletzt), Schema-Erweiterung (Konfidenz nullable + required), Item-
Normalisierung, DataFrame-Aufbau und das Top-3/Cutoff-Postprocessing der
Ergebnistabelle.
"""
import pandas as pd
import pytest

from talktrace_ai.examples.tseda import (
    TSEDA_ATTRIBUTION,
    TSEDA_CODEBOOK,
    TSEDA_PRESETS,
)
from talktrace_ai.utils.llm_analysis._schema import (
    build_analysis_schema,
    extract_shortcodes,
)
from talktrace_ai.utils.llm_analysis._json import _extract_items_by_schema
from talktrace_ai.utils.llm_analysis._shared import analysis_items_to_df
from talktrace_ai.utils.llm_analysis._stream_parse import (
    normalize_item,
    parse_jsonl_line,
)
from talktrace_ai.utils.qualitative import (
    MAX_CODES_PER_TURN,
    aggregate_multicoded,
    build_qual_stats_df,
    code_column_names,
    collect_codes,
    primary_code_series,
    strip_confidence,
    uncoded_turns,
)


# ---------------------------------------------------------------------------
# T-SEDA-Vorlage
# ---------------------------------------------------------------------------

# Reihenfolge = offizielle Detailfassung (Pack-Folien 33–38); der Crosswalk
# spiegelt sie 1:1 (dt. R=Reflexion ↔ engl. RD; dt. N=Begründen ↔ engl. R).
_EXPECTED_DE = ["I", "EI", "H", "N", "EN", "ZK", "R", "V", "L", "ÄN"]
_EXPECTED_EN = ["B", "IB", "CH", "R", "IR", "CA", "RD", "C", "G", "E"]


def test_tseda_codebook_codes():
    assert extract_shortcodes(TSEDA_CODEBOOK["de"]) == _EXPECTED_DE
    assert extract_shortcodes(TSEDA_CODEBOOK["en"]) == _EXPECTED_EN


def test_tseda_codebook_shape_matches_docx_import():
    # Gleiche Form wie ein docx-Tabellen-Import: list[dict] mit konstanten Keys.
    for entry in TSEDA_CODEBOOK["de"]:
        assert set(entry.keys()) == {"Code", "Bezeichnung", "Beschreibung"}
        assert entry["Beschreibung"].strip()
    for entry in TSEDA_CODEBOOK["en"]:
        assert set(entry.keys()) == {"Code", "Label", "Description"}
        assert entry["Description"].strip()


def test_tseda_catchall_is_last():
    # Position = Fallback-Hierarchie: die Auffang-Kategorie muss zuletzt stehen,
    # damit sie im Single-Coding-Modus nie einen spezifischeren Code verdrängt.
    assert TSEDA_CODEBOOK["de"][-1]["Code"] == "ÄN"
    assert TSEDA_CODEBOOK["en"][-1]["Code"] == "E"


def test_tseda_presets():
    assert TSEDA_PRESETS["llm_switch"] is True
    assert TSEDA_PRESETS["analyse_teacher_switch"] is True
    assert TSEDA_PRESETS["analyse_students_switch"] is False
    assert TSEDA_PRESETS["multi_coding_switch"] is True


def test_tseda_attribution_names_cambridge():
    assert "Cambridge" in TSEDA_ATTRIBUTION
    assert "CC BY" in TSEDA_ATTRIBUTION


# ---------------------------------------------------------------------------
# Schema: Konfidenz nullable + required (OpenAI-strict-kompatibel)
# ---------------------------------------------------------------------------

def test_schema_has_nullable_required_confidence():
    schema = build_analysis_schema(TSEDA_CODEBOOK["de"], "LEHRER: Hallo.\nS01: Hi.")
    items = schema["properties"]["analysis"]["items"]
    assert items["properties"]["Konfidenz"]["type"] == ["integer", "null"]
    assert "Konfidenz" in items["required"]
    # Konfidenz als LETZTES Feld definiert (Recovery-Parser-Kontrakt).
    assert list(items["properties"].keys())[-1] == "Konfidenz"


# ---------------------------------------------------------------------------
# Parsing: normalize_item / JSONL / Recovery
# ---------------------------------------------------------------------------

def test_normalize_item_passes_confidence_through():
    item = normalize_item({"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN",
                           "Impuls": "Warum?", "Konfidenz": 85})
    assert item["Konfidenz"] == 85


def test_normalize_item_clamps_and_coerces_confidence():
    assert normalize_item({"Shortcode": "EN", "Impuls": "x", "Konfidenz": 250})["Konfidenz"] == 100
    assert normalize_item({"Shortcode": "EN", "Impuls": "x", "Konfidenz": -3})["Konfidenz"] == 0
    assert normalize_item({"Shortcode": "EN", "Impuls": "x", "Konfidenz": "72"})["Konfidenz"] == 72


def test_normalize_item_without_confidence_keeps_legacy_shape():
    item = normalize_item({"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN", "Impuls": "Warum?"})
    assert "Konfidenz" not in item
    # Explizites null (Single-Coding mit strict-Schema) bleibt ebenfalls draußen.
    item = normalize_item({"Shortcode": "EN", "Impuls": "x", "Konfidenz": None})
    assert "Konfidenz" not in item


def test_parse_jsonl_line_with_confidence():
    line = '{"#": 3, "Sprecher": "LEHRER", "Shortcode": "EN", "Impuls": "Warum?", "Konfidenz": 90}'
    assert parse_jsonl_line(line)["Konfidenz"] == 90


def test_recovery_parser_captures_trailing_confidence():
    text = (
        '{"analysis": ['
        '{"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN", "Impuls": "Warum "denn" so?", "Konfidenz": 77},'
        '{"#": 2, "Sprecher": "S01", "Shortcode": "N", "Impuls": "Weil."}'
        ']}'
    )
    items = _extract_items_by_schema(text)
    assert len(items) == 2
    assert items[0]["Konfidenz"] == 77
    assert "Konfidenz" not in items[1]


# ---------------------------------------------------------------------------
# DataFrame-Aufbau
# ---------------------------------------------------------------------------

def test_items_to_df_without_confidence_keeps_four_columns():
    df = analysis_items_to_df([
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN", "Impuls": "Warum?"},
    ])
    assert list(df.columns) == ["#", "Sprecher", "Shortcode", "Impuls"]


def test_items_to_df_with_confidence_adds_column():
    df = analysis_items_to_df([
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN", "Impuls": "Warum?", "Konfidenz": 80},
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "L", "Impuls": "Warum?"},
    ])
    assert list(df.columns) == ["#", "Sprecher", "Shortcode", "Impuls", "Konfidenz"]
    assert df["Konfidenz"].tolist()[0] == 80


def test_items_to_df_empty():
    df = analysis_items_to_df([])
    assert list(df.columns) == ["#", "Sprecher", "Shortcode", "Impuls"]
    assert df.empty


# ---------------------------------------------------------------------------
# Postprocessing: Top-3-Spalten, Konfidenz-Sortierung, Anzeige-Format
# ---------------------------------------------------------------------------

def _coded(rows):
    """rows: list of (key, code, priority, konfidenz|None)"""
    return pd.DataFrame(
        [{"__key__": k, "Shortcode": c, "__priority__": p, "Konfidenz": v}
         for k, c, p, v in rows]
    ).sort_values("__priority__", kind="mergesort")


def _wide(out):
    return out[["__code1__", "__code2__"]].values.tolist()


def test_aggregate_caps_top2_no_cutoff():
    # Kein Konfidenz-Filter: auch unsichere Kandidaten erscheinen — aber
    # höchstens zwei (T-SEDA-Regel: 0–2 Codes pro Turn), Konfidenz absteigend.
    coded = _coded([
        ("t1", "EN", 4, 95),
        ("t1", "H", 3, 40),     # unter 50 — bleibt grundsätzlich sichtbar …
        ("t1", "EI", 1, 60),
        ("t1", "ÄN", 10, 25),
    ])
    out = aggregate_multicoded(coded)
    # … fällt hier aber dem Top-2-Cap zum Opfer (Plätze 3+4 gekappt).
    assert _wide(out) == [["EN (95 %)", "EI (60 %)"]]
    assert MAX_CODES_PER_TURN == 2


def test_aggregate_shows_uncertain_candidate_below_50():
    coded = _coded([
        ("t1", "EN", 4, 95),
        ("t1", "H", 3, 35),    # unsicher — erscheint trotzdem mit Konfidenz
    ])
    out = aggregate_multicoded(coded)
    assert _wide(out) == [["EN (95 %)", "H (35 %)"]]


def test_aggregate_orders_by_confidence_not_priority():
    coded = _coded([
        ("t1", "EI", 1, 60),   # höchste Codebuch-Priorität, aber geringere Konfidenz
        ("t1", "L", 9, 90),
    ])
    out = aggregate_multicoded(coded)
    assert _wide(out) == [["L (90 %)", "EI (60 %)"]]


def test_aggregate_dedupes_same_code_keeps_highest_confidence():
    coded = _coded([
        ("t1", "EN", 4, 60),
        ("t1", "EN", 4, 88),
    ])
    out = aggregate_multicoded(coded)
    assert _wide(out) == [["EN (88 %)", ""]]


def test_aggregate_without_confidence_column_is_priority_order():
    coded = pd.DataFrame([
        {"__key__": "t1", "Shortcode": "L", "__priority__": 9},
        {"__key__": "t1", "Shortcode": "EI", "__priority__": 1},
    ]).sort_values("__priority__", kind="mergesort")
    out = aggregate_multicoded(coded)
    # Ohne Konfidenz: Prioritäts-Reihenfolge, kein Suffix.
    assert _wide(out) == [["EI", "L"]]


def test_aggregate_rows_without_confidence_sort_last():
    # Altbestand (NaN-Konfidenz) bleibt erhalten, sortiert ans Ende.
    coded = _coded([
        ("t1", "EN", 4, 80),
        ("t1", "V", 7, None),
    ])
    out = aggregate_multicoded(coded)
    assert _wide(out) == [["EN (80 %)", "V"]]


def test_strip_confidence():
    assert strip_confidence("EN (85 %)") == "EN"
    assert strip_confidence("EN (85 %); L (62 %)") == "EN; L"
    assert strip_confidence("EN") == "EN"


def test_collect_and_primary_from_wide_table():
    cols = code_column_names(_t)
    assert len(cols) == 2
    df = pd.DataFrame({
        "#": [1, 2],
        cols[0]: ["EN (92 %)", ""],
        cols[1]: ["L (40 %)", ""],
    })
    assert sorted(collect_codes(df, _t).tolist()) == ["EN", "L"]
    assert primary_code_series(df, _t).tolist() == ["EN", ""]


def test_collect_and_primary_from_legacy_table():
    sc = _t("report", "shortcode")
    df = pd.DataFrame({"#": [1, 2], sc: ["EN (92 %); L (40 %)", ""]})
    assert sorted(collect_codes(df, _t).tolist()) == ["EN", "L"]
    assert primary_code_series(df, _t).tolist() == ["EN", ""]


# ---------------------------------------------------------------------------
# Zweite Prüfrunde: Auswahl der uncodierten, codierbaren Turns
# ---------------------------------------------------------------------------

_TRANSCRIPT_2P = (
    "LEHRER: Warum sollte das so sein?\n"
    "S1: Weil alle betroffen sind.\n"
    "LEHRER: S2\n"
    "S2: Ich stimme zu.\n"
    "LEHRER: Fassen wir zusammen.\n"
)


def test_uncoded_turns_teacher_only():
    items = [{"Sprecher": "LEHRER", "Shortcode": "EN",
              "Impuls": "Warum sollte das so sein?"}]
    pending = uncoded_turns(_TRANSCRIPT_2P, "LEHRER", items,
                            teacher_on=True, students_on=False)
    # Nur die uncodierten LEHRER-Turns — keine Schülerturns, der codierte
    # Turn fehlt ebenfalls.
    assert pending == [("LEHRER", "S2"), ("LEHRER", "Fassen wir zusammen.")]


def test_uncoded_turns_matches_tolerantly_and_via_alias():
    # LLM-Item mit generischem Sprecher-Label + Mini-Textabweichung
    # (fehlendes Satzzeichen) muss dem Transkript-Turn zugeordnet werden.
    items = [{"Sprecher": "Lehrperson", "Shortcode": "ZK",
              "Impuls": "Fassen wir zusammen"}]
    pending = uncoded_turns(_TRANSCRIPT_2P, "LEHRER", items,
                            teacher_on=True, students_on=False)
    assert ("LEHRER", "Fassen wir zusammen.") not in pending
    assert ("LEHRER", "Warum sollte das so sein?") in pending


def test_uncoded_turns_students_included_when_enabled():
    pending = uncoded_turns(_TRANSCRIPT_2P, "LEHRER", [],
                            teacher_on=True, students_on=True)
    assert ("S1", "Weil alle betroffen sind.") in pending
    assert ("S2", "Ich stimme zu.") in pending


def test_uncoded_turns_empty_transcript():
    assert uncoded_turns("", "LEHRER", []) == []


# ---------------------------------------------------------------------------
# End-to-End über build_qual_stats_df (pure Spiegelung der Ergebnistabelle)
# ---------------------------------------------------------------------------

def _t(section, key):
    from talktrace_ai.localization.translation import TRANSLATIONS
    return TRANSLATIONS["de"][section][key]


def test_build_qual_stats_df_multicoding_wide_columns():
    # Einstelliges Schülerlabel (S1) mit Absicht: der Parser-Fix (S\d{1,3})
    # muss den Turn in die Tabelle bringen.
    transcript = "LEHRER: Warum sollte das so sein?\nS1: Weil alle betroffen sind."
    analysis_df = analysis_items_to_df([
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN",
         "Impuls": "Warum sollte das so sein?", "Konfidenz": 92},
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "L",
         "Impuls": "Warum sollte das so sein?", "Konfidenz": 61},
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "ÄN",
         "Impuls": "Warum sollte das so sein?", "Konfidenz": 30},
    ])
    merged = build_qual_stats_df(
        analysis_df, transcript, "LEHRER", TSEDA_CODEBOOK["de"],
        multi_coding=True, t=_t,
    )
    c1, c2 = code_column_names(_t)
    # Alle Turns des Gesprächs erscheinen — auch der (uncodierte) S1-Turn.
    assert len(merged) == 2
    # Top-2-Kandidaten sichtbar (Konfidenz absteigend); Platz 3 (ÄN, 30 %)
    # fällt dem Cap zum Opfer.
    assert merged[c1].tolist() == ["EN (92 %)", ""]
    assert merged[c2].tolist() == ["L (61 %)", ""]


def test_build_qual_stats_df_single_coding_ignores_confidence():
    transcript = "LEHRER: Warum sollte das so sein?"
    analysis_df = analysis_items_to_df([
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "L",
         "Impuls": "Warum sollte das so sein?", "Konfidenz": 90},
        {"#": 1, "Sprecher": "LEHRER", "Shortcode": "EN",
         "Impuls": "Warum sollte das so sein?", "Konfidenz": 70},
    ])
    merged = build_qual_stats_df(
        analysis_df, transcript, "LEHRER", TSEDA_CODEBOOK["de"],
        multi_coding=False, t=_t,
    )
    sc_col = _t("report", "shortcode")
    # Single-Coding bleibt beim Hierarchie-Kontrakt: EN steht im Codebuch
    # vor L und gewinnt unabhängig von der Konfidenz — kein Suffix, und
    # die klassische Einzel-Spalte (keine Code-1..3-Spalten).
    assert merged[sc_col].tolist() == ["EN"]
    assert not any(c in merged.columns for c in code_column_names(_t))
