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
    CONFIDENCE_CUTOFF,
    MAX_CODES_PER_TURN,
    aggregate_multicoded,
    build_qual_stats_df,
    strip_confidence,
)


# ---------------------------------------------------------------------------
# T-SEDA-Vorlage
# ---------------------------------------------------------------------------

_EXPECTED_DE = ["EI", "I", "H", "EN", "N", "ZK", "V", "R", "L", "ÄN"]
_EXPECTED_EN = ["IB", "B", "CH", "IR", "R", "CA", "C", "RD", "G", "E"]


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
# Postprocessing: Cutoff, Top-3, Anzeige-Format
# ---------------------------------------------------------------------------

def _coded(rows):
    """rows: list of (key, code, priority, konfidenz|None)"""
    return pd.DataFrame(
        [{"__key__": k, "Shortcode": c, "__priority__": p, "Konfidenz": v}
         for k, c, p, v in rows]
    ).sort_values("__priority__", kind="mergesort")


def test_aggregate_filters_cutoff_and_caps_top3():
    coded = _coded([
        ("t1", "EN", 4, 95),
        ("t1", "L", 9, 70),
        ("t1", "EI", 1, 60),
        ("t1", "ÄN", 10, 55),   # Platz 4 — fällt dem Top-3-Cap zum Opfer
        ("t1", "H", 3, 40),     # unter Cutoff — gefiltert
    ])
    out = aggregate_multicoded(coded)
    assert out["Shortcode"].tolist() == ["EN (95 %); L (70 %); EI (60 %)"]


def test_aggregate_orders_by_confidence_not_priority():
    coded = _coded([
        ("t1", "EI", 1, 60),   # höchste Codebuch-Priorität, aber geringere Konfidenz
        ("t1", "L", 9, 90),
    ])
    out = aggregate_multicoded(coded)
    assert out["Shortcode"].tolist() == ["L (90 %); EI (60 %)"]


def test_aggregate_dedupes_same_code_keeps_highest_confidence():
    coded = _coded([
        ("t1", "EN", 4, 60),
        ("t1", "EN", 4, 88),
    ])
    out = aggregate_multicoded(coded)
    assert out["Shortcode"].tolist() == ["EN (88 %)"]


def test_aggregate_boundary_exactly_50_is_dropped():
    # Yutas Vorgabe: "über 50 %" — 50 selbst fällt raus.
    coded = _coded([("t1", "EN", 4, 50), ("t1", "L", 9, 51)])
    out = aggregate_multicoded(coded)
    assert out["Shortcode"].tolist() == ["L (51 %)"]
    assert CONFIDENCE_CUTOFF == 50
    assert MAX_CODES_PER_TURN == 3


def test_aggregate_without_confidence_column_is_legacy_join():
    coded = pd.DataFrame([
        {"__key__": "t1", "Shortcode": "L", "__priority__": 9},
        {"__key__": "t1", "Shortcode": "EI", "__priority__": 1},
    ]).sort_values("__priority__", kind="mergesort")
    out = aggregate_multicoded(coded)
    # Ohne Konfidenz: Prioritäts-Reihenfolge, kein Suffix.
    assert out["Shortcode"].tolist() == ["EI; L"]


def test_aggregate_rows_without_confidence_survive_filter():
    # Altbestand (NaN-Konfidenz) bleibt erhalten, sortiert ans Ende.
    coded = _coded([
        ("t1", "EN", 4, 80),
        ("t1", "V", 7, None),
    ])
    out = aggregate_multicoded(coded)
    assert out["Shortcode"].tolist() == ["EN (80 %); V"]


def test_strip_confidence():
    assert strip_confidence("EN (85 %)") == "EN"
    assert strip_confidence("EN (85 %); L (62 %)") == "EN; L"
    assert strip_confidence("EN") == "EN"


# ---------------------------------------------------------------------------
# End-to-End über build_qual_stats_df (pure Spiegelung der Ergebnistabelle)
# ---------------------------------------------------------------------------

def _t(section, key):
    from talktrace_ai.localization.translation import TRANSLATIONS
    return TRANSLATIONS["de"][section][key]


def test_build_qual_stats_df_multicoding_with_confidence():
    transcript = "LEHRER: Warum sollte das so sein?\nS01: Weil alle betroffen sind."
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
    sc_col = _t("report", "shortcode")
    assert merged[sc_col].tolist()[0] == "EN (92 %); L (61 %)"
    # Uncodierter Schüler-Turn bleibt leer.
    assert merged[sc_col].tolist()[1] == ""


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
    # vor L und gewinnt unabhängig von der Konfidenz — kein Suffix.
    assert merged[sc_col].tolist() == ["EN"]
