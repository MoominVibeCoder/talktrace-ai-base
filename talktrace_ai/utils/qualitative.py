"""Pure helpers for the quantitative + qualitative plots / tables.

Both the manual results pipeline (handlers/results.py) and the autopilot
report builder (handlers/autopilot.py) need to compute the same per-coding
artefacts: the merged 'qualitative stats' DataFrame and its bar plot, plus
the speaker-words distribution plot. Extracting these into pure functions
lets the autopilot generate per-coder reports without temporarily mutating
the global reactive state.
"""
import re

import matplotlib.pyplot as plt
import pandas as pd

from .codebook_hierarchy import build_priority_lookup, priority_for
from .plot_style import (
    apply_axes_style,
    primary_color,
    round_bar_corners,
    style_no_data_axes,
)
from .stats import _parse_turns


# --- Multi-Coding mit Konfidenz -------------------------------------------
# Multi-Coding zeigt pro Turn bis zu MAX_CODES_PER_TURN Kandidaten-Codes in
# EIGENEN Spalten ("Code 1", "Code 2"), jeweils als "EN (92 %)". Bewusst OHNE
# Konfidenz-Schwelle: auch unsichere Kandidaten erscheinen — die Konfidenz
# steht dabei, die Bewertung liegt beim Menschen. Das Top-N-Cap bleibt als
# Post-Processing-Sicherheitsnetz zur gleichlautenden Prompt-Instruktion
# (localization: *_multi_coding_on). Cap = 2, konsistent zur T-SEDA-Regel
# „0–2 Codes pro Turn".
MAX_CODES_PER_TURN = 2

_CONF_SUFFIX_RE = re.compile(r"\s*\(\d+\s*%\)")


def strip_confidence(text) -> str:
    """Entfernt " (NN %)"-Konfidenz-Suffixe aus einer Shortcode-Zelle."""
    return _CONF_SUFFIX_RE.sub("", str(text))


def code_column_names(t) -> list:
    """Lokalisierte Spaltennamen der Multi-Coding-Anzeige ("Code 1".."Code 3")."""
    base = t("report", "shortcode")
    return [f"{base} {i}" for i in range(1, MAX_CODES_PER_TURN + 1)]


_WIDE_KEY_COLUMNS = [f"__code{i}__" for i in range(1, MAX_CODES_PER_TURN + 1)]


def aggregate_multicoded(coded):
    """Codes pro Turn (``__key__``) auf Anzeige-Spalten verteilen.

    Erwartet einen DataFrame mit ``__key__``, ``Shortcode`` und optional
    ``Konfidenz``, bereits stabil nach ``__priority__`` sortiert. Mit
    Konfidenz: Sortierung nach Konfidenz absteigend (Codebuch-Priorität als
    Tiebreaker), Anzeige "CODE (NN %)"; ohne Konfidenz-Spalte bleibt die
    Prioritäts-Reihenfolge (reine Codes). Duplikate desselben Codes pro Turn
    werden dedupliziert (höchste Konfidenz gewinnt), höchstens
    MAX_CODES_PER_TURN Codes pro Turn. Gibt einen DataFrame mit ``__key__``
    + ``__code1__``..``__code3__`` zurück (fehlende Plätze = "").
    """
    coded = coded.copy()
    coded["__code__"] = coded["Shortcode"].astype(str).str.strip()
    coded = coded[coded["__code__"] != ""]
    if "Konfidenz" in coded.columns:
        coded["__conf__"] = pd.to_numeric(coded["Konfidenz"], errors="coerce")
        # Stabiler Sort auf bereits prioritäts-sortierten Zeilen: Konfidenz
        # wird Primärkriterium, die Codebuch-Priorität bleibt Tiebreaker.
        coded = coded.sort_values(
            "__conf__", ascending=False, kind="mergesort", na_position="last"
        )
        # Emittiert das Modell denselben Code mehrfach für einen Turn,
        # gewinnt die höchste Konfidenz.
        coded = coded.drop_duplicates(subset=["__key__", "__code__"], keep="first")
        coded["__display__"] = [
            f"{c} ({int(v)} %)" if pd.notna(v) else c
            for c, v in zip(coded["__code__"], coded["__conf__"])
        ]
    else:
        coded = coded.drop_duplicates(subset=["__key__", "__code__"], keep="first")
        coded["__display__"] = coded["__code__"]
    coded = coded.groupby("__key__", sort=False).head(MAX_CODES_PER_TURN)
    grouped = coded.groupby("__key__", sort=False)["__display__"].agg(list)
    out = pd.DataFrame({"__key__": grouped.index})
    lists = grouped.tolist()
    for i, col in enumerate(_WIDE_KEY_COLUMNS):
        out[col] = [lst[i] if i < len(lst) else "" for lst in lists]
    return out


def collect_codes(df, t):
    """Serie einzelner reiner Codes aus einer Ergebnis-Tabelle — ALLE
    Kandidaten, inklusive Nebencodes.

    Versteht beide Formen: die Multi-Coding-Spalten ("Code 1", "Code 2")
    und die klassische Einzel-Spalte (ggf. mit "; "-gejointen Altwerten).
    Konfidenz-Suffixe werden gestrippt, Leerwerte entfernt. Hinweis: die
    Häufigkeits-Auswertungen (Plot, Modus) zählen bewusst nur den primären
    Code — siehe primary_code_series.
    """
    wide = [c for c in code_column_names(t) if c in df.columns]
    if wide:
        s = pd.concat([df[c] for c in wide], ignore_index=True)
    else:
        sc = t("report", "shortcode")
        if sc not in df.columns:
            return pd.Series(dtype=str)
        s = df[sc].astype(str).str.strip().str.split(r"\s*;\s*", regex=True).explode()
    s = s.astype(str).apply(strip_confidence).str.strip()
    return s[s != ""]


def primary_code_series(df, t):
    """Erster (bester) Code pro Turn als reine Code-Serie — für die
    Übergangsmatrix und Zählungen "codiert ja/nein". Versteht beide
    Tabellen-Formen (siehe collect_codes); uncodierte Turns → ""."""
    first_wide = code_column_names(t)[0]
    if first_wide in df.columns:
        s = df[first_wide]
    else:
        sc = t("report", "shortcode")
        if sc not in df.columns:
            return pd.Series(dtype=str)
        s = df[sc]
    s = s.astype(str).apply(strip_confidence).str.strip()
    return s.str.split(r"\s*;\s*", regex=True).str[0].fillna("")


def norm_impuls(s):
    """Toleranter Merge-Schlüssel für Impuls-Texte: lowercase, Rand-
    Interpunktion gestrippt, Whitespace kollabiert. LLMs geben Impulse
    häufig mit Mini-Abweichungen zurück (Punkt am Ende, normalisierte
    Anführungszeichen) — Exakt-Match ließe die Zuordnung leerlaufen."""
    t_ = re.sub(r"\s+", " ", str(s)).strip()
    return re.sub(
        r"^[\s\"'„“”»«()\[\]\.…!?,:;-]+|[\s\"'„“”»«()\[\]\.…!?,:;-]+$",
        "",
        t_,
    ).lower()


# Sprecher-Aliasse: LLMs benennen die Lehrkraft gern generisch, auch wenn
# das Transkript ein konfiguriertes Label nutzt.
_TEACHER_ALIAS_BASE = {"lehrperson", "lehrer", "lehrkraft", "teacher"}


def uncoded_turns(transcript_text, teacher_name, analysis_items,
                  *, teacher_on=True, students_on=True):
    """Turns der gewählten Sprechergruppe, die (noch) keine Codierung tragen.

    Grundlage der zweiten Prüfrunde: nur Turns, die überhaupt codierbar
    gewesen wären (Speaker-Filter!), werden dem LLM erneut vorgelegt —
    bei „nur Lehrkraft" also keine Schülerturns. Matching wie der
    Ergebnis-Merge (norm_impuls + Lehrkraft-Aliasse). Gibt eine Liste
    von (Sprecher, Äußerung) in Transkript-Reihenfolge zurück.
    """
    if not transcript_text:
        return []
    teacher_name = str(teacher_name or "")
    aliases = _TEACHER_ALIAS_BASE | {teacher_name.lower()}
    coded_keys = set()
    for it in analysis_items or []:
        if not isinstance(it, dict):
            continue
        spk = str(it.get("Sprecher", ""))
        spk = teacher_name if spk.lower() in aliases else spk
        coded_keys.add(f"{spk} :: {norm_impuls(it.get('Impuls', ''))}")
    out = []
    for spk, utt in _parse_turns(transcript_text, teacher_name):
        is_teacher = str(spk).lower() == teacher_name.lower()
        if is_teacher and not teacher_on:
            continue
        if not is_teacher and not students_on:
            continue
        if not str(utt).strip():
            continue
        if f"{spk} :: {norm_impuls(utt)}" in coded_keys:
            continue
        out.append((spk, utt))
    return out


def build_qual_stats_df(
    analysis_df,
    transcript_text,
    teacher_name,
    codebook_data,
    multi_coding,
    t,
    converted_transcript=None,
):
    """Merge an LLM coding DataFrame with the parsed transcript turns.

    Mirrors handlers/results.py:make_qualitative_stats_df but takes all
    inputs as plain values so callers don't need to be inside a reactive
    context. Returns the merged DataFrame with the localized column names.
    """
    # Multi-Coding: pro Turn bis zu drei Code-Spalten ("Code 1".."Code 3");
    # Single-Coding: die klassische Einzel-Spalte.
    if multi_coding:
        cols = [
            "#",
            t("report", "speaker"),
            t("report", "teacher_statement"),
            *code_column_names(t),
        ]
    else:
        cols = [
            "#",
            t("report", "speaker"),
            t("report", "teacher_statement"),
            t("report", "shortcode"),
        ]
    if analysis_df is None:
        return pd.DataFrame(columns=cols)
    analysis_df = analysis_df.copy()
    if analysis_df.empty:
        return pd.DataFrame(columns=cols)
    if "Sprecher" not in analysis_df.columns:
        analysis_df["Sprecher"] = ""

    if not transcript_text and converted_transcript:
        if isinstance(converted_transcript, dict):
            transcript_text = converted_transcript.get("text")

    if not transcript_text:
        # Fallback ohne Transkript: rohe codierte Items (eine Zeile pro Code)
        # in der klassischen 4-Spalten-Form — unabhängig vom Multi-Schalter.
        analysis_df["#"] = analysis_df.reset_index().index + 1
        analysis_df = analysis_df[["#", "Sprecher", "Impuls", "Shortcode"]]
        analysis_df.columns = [
            "#",
            t("report", "speaker"),
            t("report", "teacher_statement"),
            t("report", "shortcode"),
        ]
        return analysis_df

    turns = _parse_turns(transcript_text, teacher_name)
    all_turns_df = pd.DataFrame(turns, columns=["Sprecher", "Impuls"])
    all_turns_df["Sprecher"] = all_turns_df["Sprecher"].apply(
        lambda s: teacher_name if s.lower() == teacher_name.lower() else s
    )
    all_turns_df["#"] = range(1, len(all_turns_df) + 1)

    # Modul-Funktion norm_impuls — gleiche Normalisierung wie uncoded_turns.
    _norm_impuls = norm_impuls

    all_turns_df["__key__"] = (
        all_turns_df["Sprecher"] + " :: " + all_turns_df["Impuls"].apply(_norm_impuls)
    )
    coded_cols = ["Sprecher", "Impuls", "Shortcode"]
    if "Konfidenz" in analysis_df.columns:
        coded_cols.append("Konfidenz")
    coded = analysis_df[coded_cols].copy()
    _teacher_aliases = {"lehrperson", "lehrer", "lehrkraft", "teacher",
                        teacher_name.lower()}
    coded["Sprecher"] = coded["Sprecher"].apply(
        lambda s: teacher_name if str(s).lower() in _teacher_aliases else s
    )
    coded["__key__"] = (
        coded["Sprecher"] + " :: " + coded["Impuls"].apply(_norm_impuls)
    )
    _priority_lookup = build_priority_lookup(codebook_data)
    coded["__priority__"] = coded["Shortcode"].apply(
        lambda c: priority_for(_priority_lookup, str(c).strip())
    )
    coded = coded.sort_values("__priority__", kind="mergesort")
    if multi_coding:
        # Top-3 pro Turn auf eigene Spalten verteilt (Konfidenz absteigend,
        # "CODE (NN %)"-Anzeige) — ohne Konfidenz-Schwelle.
        coded = aggregate_multicoded(coded)
        merged = pd.merge(all_turns_df, coded, on="__key__", how="left")
        merged = merged.drop(columns=["__key__"])
        merged = merged[["#", "Sprecher", "Impuls", *_WIDE_KEY_COLUMNS]].copy()
        for c in _WIDE_KEY_COLUMNS:
            merged[c] = merged[c].fillna("").astype(str)
        merged.columns = cols
        return merged
    coded = coded.drop_duplicates(subset=["__key__"], keep="first")
    coded = coded.drop(columns=["__priority__"])
    merged = pd.merge(
        all_turns_df,
        coded[["__key__", "Shortcode"]],
        on="__key__",
        how="left",
    )
    merged = merged.drop(columns=["__key__"])
    merged = merged[["#", "Sprecher", "Impuls", "Shortcode"]].copy()
    merged["Shortcode"] = merged["Shortcode"].fillna("").astype(str)
    merged.columns = cols
    return merged


def build_qual_plot(merged_df, t, mode="light"):
    """Bar plot of code frequencies. Returns a matplotlib axes (always)."""
    if merged_df is None or merged_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, t("results", "no_data"),
                ha="center", va="center", fontsize=12)
        ax.axis("off")
        style_no_data_axes(ax, mode)
        return ax
    shortcode_col = t("report", "shortcode")
    # Nur der PRIMÄRE Code (Shortcode 1) zählt in die Häufigkeiten —
    # gleiche Regel wie der Plot im Results-Handler. primary_code_series
    # versteht beide Tabellen-Formen und strippt Konfidenz-Suffixe.
    codes = primary_code_series(merged_df, t)
    codes = codes[codes != ""]
    if codes.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, t("results", "no_data"),
                ha="center", va="center", fontsize=12)
        ax.axis("off")
        style_no_data_axes(ax, mode)
        return ax
    analysis_plot = (
        codes.value_counts()
        .sort_index()
        .rename_axis(shortcode_col)
        .reset_index(name="Anzahl")
        .plot(
            kind="bar",
            x=shortcode_col,
            y="Anzahl",
            alpha=1,
            rot=0,
            width=0.55,
            color=primary_color(mode),
        )
    )
    analysis_plot.set_xlabel(t("report", "shortcode"))
    plt.setp(analysis_plot.get_xticklabels(), rotation=45, ha="right")
    analysis_plot.set_ylabel(t("report", "quantity"))
    legend = analysis_plot.get_legend()
    if legend is not None:
        legend.remove()
    for container in analysis_plot.containers:
        analysis_plot.bar_label(container, label_type="edge")
    round_bar_corners(analysis_plot)
    apply_axes_style(analysis_plot, mode)
    return analysis_plot


def build_sim_plot(stats_df, teacher_name, t, mode="light"):
    """Speaker-words distribution. Returns a matplotlib axes or None."""
    if stats_df is None or len(stats_df) == 0:
        return None
    distribution = stats_df.plot(
        kind="bar",
        x="Sprecher",
        y="Gesamt_Woerter",
        alpha=1,
        rot=0,
        width=0.55,
        color=primary_color(mode),
    )
    distribution.set_xlabel(t("results", "words_total"))
    distribution.set_ylabel(t("results", "quantity"))
    legend = distribution.get_legend()
    if legend is not None:
        legend.remove()
    total = stats_df["Gesamt_Woerter"].sum() or 1
    teacher_label = t("stats", "teacher")
    students_label = t("stats", "students")
    tick_labels = [
        teacher_label if str(spk) == teacher_name else students_label
        for spk in stats_df["Sprecher"].tolist()
    ]
    distribution.set_xticks(range(len(tick_labels)))
    distribution.set_xticklabels(tick_labels)
    for container in distribution.containers:
        perc_labels = [
            f"{(bar.get_height() / total * 100):.1f}%" for bar in container
        ]
        distribution.bar_label(container, label_type="center")
        distribution.bar_label(container, labels=perc_labels, label_type="edge")
    round_bar_corners(distribution)
    apply_axes_style(distribution, mode)
    return distribution
