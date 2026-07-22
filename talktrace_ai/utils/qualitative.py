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
    secondary_color,
    style_no_data_axes,
)
from .stats import _parse_turns, code_distribution_over_time


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


# --- Konfidenz-Bänder -----------------------------------------------------
# Schwellen bewusst IDENTISCH zu den Kalibrier-Ankern im Prompt
# (localization: *_multi_coding_on): "90+ NUR bei eindeutiger, wörtlich
# belegbarer Passung" und "unter 50 = spekulativ". Anzeige und Kalibrierung
# müssen dieselbe Sprache sprechen — sonst markiert der Report als sicher,
# was das Modell laut Instruktion nicht als sicher gemeint hat. Wer hier
# etwas ändert, ändert auch den Prompt (und umgekehrt).
CONFIDENCE_HIGH_MIN = 90
CONFIDENCE_LOW_MAX = 49  # alles darunter/gleich gilt als spekulativ

_CONF_VALUE_RE = re.compile(r"\((\d+)\s*%\)")


def extract_confidence(text):
    """Konfidenzwert aus einer Shortcode-Zelle ("EN (92 %)") als int.

    Gegenstück zu strip_confidence. None, wenn die Zelle keinen Wert trägt —
    im Single-Coding-Modus und bei handkorrigierten Zellen ist das der
    Normalfall, nicht der Fehlerfall.
    """
    m = _CONF_VALUE_RE.search(str(text))
    return int(m.group(1)) if m else None


def confidence_band(value):
    """Band einer Konfidenz: "high" | "medium" | "low" | None.

    None heißt "keine Konfidenz-Information" (nicht "niedrig") — eine
    handkorrigierte Zelle darf nicht wie eine spekulative Modell-Zuordnung
    aussehen.
    """
    if value is None:
        return None
    if value >= CONFIDENCE_HIGH_MIN:
        return "high"
    if value <= CONFIDENCE_LOW_MAX:
        return "low"
    return "medium"


def confidence_band_of_cell(text):
    """Band direkt aus einer Shortcode-Zelle — Kurzform für die Renderer."""
    return confidence_band(extract_confidence(text))


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


def _with_confidence(codes, confidences):
    """Shortcodes als "CODE (NN %)" formatieren — gleiches Anzeigeformat wie
    aggregate_multicoded, damit Report-Shading (confidence_band_of_cell) und
    strip_confidence auch im Single-Coding greifen. Leere Codes bzw. fehlende
    Konfidenzen bleiben unformatiert."""
    conf = pd.to_numeric(confidences, errors="coerce")
    return [
        f"{str(c).strip()} ({int(v)} %)" if str(c).strip() and pd.notna(v) else str(c).strip()
        for c, v in zip(codes, conf)
    ]


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


def primary_code_over_time(merged_df, t, n_segments=3, segment_labels=None):
    """Zeitverlaufs-Verteilung der PRIMÄRcodes (Shortcode 1) je Abschnitt.

    Erwartet die zusammengeführte All-Turns-Tabelle (eine Zeile pro Turn in
    Transkript-Reihenfolge, uncodierte Turns mit leerem Code). Zählt je Turn
    nur den primären Code — gleiche Regel wie Balken, "Häufigster Code"-Chip
    und Übergangsmatrix; die Nebenkandidaten aus Spalte 2 verzerren den
    Verlauf nicht mehr. Der Turn-Index ist die Zeilenposition (= reale
    Transkript-Reihenfolge, uncodierte Turns eingeschlossen), sodass die
    Abschnittsgrenzen sitzen. Gibt denselben DataFrame wie
    code_distribution_over_time zurück (Abschnitt/Shortcode/Anteil/Anzahl).
    """
    if merged_df is None or merged_df.empty:
        return code_distribution_over_time(
            None, 0, n_segments=n_segments, segment_labels=segment_labels
        )
    total_turns = len(merged_df)
    mapped = pd.DataFrame({
        "turn_index": range(total_turns),
        "Shortcode": primary_code_series(merged_df, t).to_numpy(),
    })
    return code_distribution_over_time(
        mapped, total_turns,
        n_segments=n_segments, segment_labels=segment_labels,
    )


# Sprecher-Aliasse: LLMs benennen die Lehrkraft gern generisch, auch wenn
# das Transkript ein konfiguriertes Label nutzt.
_TEACHER_ALIAS_BASE = {"lehrperson", "lehrer", "lehrkraft", "teacher"}


def speaker_group_mask(merged_df, t, teacher_name):
    """Boolesche Serie: True = Turn stammt von der Lehrkraft.

    Grundlage jeder Rollen-Auswertung (Balken, Verteilungstabelle). Nutzt die
    Sprecher-Spalte der zusammengeführten Tabelle, die build_qual_stats_df
    bereits auf die kanonische Schreibweise normalisiert hat; die Aliasse
    fangen zusätzlich den Fallback-Pfad ohne Transkript ab, in dem die roh
    vom LLM gelieferten Sprecherlabels stehen. Fehlt die Spalte oder der
    Lehrkraft-Name, ist die Maske durchgehend False (→ keine Aufteilung).
    """
    speaker_col = t("report", "speaker")
    if merged_df is None or speaker_col not in merged_df.columns:
        return pd.Series(False, index=getattr(merged_df, "index", None))
    teacher_name = str(teacher_name or "").strip()
    if not teacher_name:
        return pd.Series(False, index=merged_df.index)
    aliases = _TEACHER_ALIAS_BASE | {teacher_name.lower()}
    return merged_df[speaker_col].astype(str).str.strip().str.lower().isin(aliases)


def code_counts_by_group(merged_df, t, teacher_name):
    """Häufigkeit je Code, aufgeteilt nach Lehrkraft und Schüler:innen.

    Zählt wie alle anderen Häufigkeits-Auswertungen nur den PRIMÄRcode
    (Shortcode 1). Gibt einen DataFrame mit Index = Code (alphabetisch) und
    den beiden lokalisierten Spalten zurück; leer, wenn nichts codiert ist.
    Gemeinsame Datenbasis von Balkenplot und Report-Verteilungstabelle, damit
    beide nicht auseinanderlaufen können.
    """
    teacher_label = t("report", "teacher")
    pupils_label = t("report", "pupils")
    empty = pd.DataFrame(columns=[teacher_label, pupils_label], dtype=int)
    if merged_df is None or merged_df.empty:
        return empty
    codes = primary_code_series(merged_df, t)
    is_teacher = speaker_group_mask(merged_df, t, teacher_name)
    keep = codes != ""
    if not keep.any():
        return empty
    out = pd.DataFrame({"__code__": codes[keep], "__teacher__": is_teacher[keep]})
    counts = (
        out.groupby("__code__")["__teacher__"]
        .agg(**{teacher_label: "sum", pupils_label: lambda s: (~s).sum()})
        .sort_index()
        .astype(int)
    )
    counts.index.name = t("report", "shortcode")
    return counts


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


def has_multicoded_turns(analysis_df) -> bool:
    """True, wenn irgendein Turn mehr als einen Code trägt (echtes Multi-Coding).

    Datengetriebenes Multi-Signal für geladene Sessions, deren Switch (nur bei
    aktivem llm_switch gerendert) aus ist. Bewusst NICHT an der Konfidenz-Spalte
    festgemacht: die trägt seit der Härtung auch Single-Coding, taugt also nicht
    mehr als Unterscheidung. Multi-Coding emittiert denselben Turn (Sprecher +
    Impuls) mehrfach mit verschiedenem Shortcode — genau das prüfen wir."""
    if analysis_df is None or analysis_df.empty:
        return False
    if not {"Sprecher", "Impuls"}.issubset(analysis_df.columns):
        return False
    key = analysis_df["Sprecher"].astype(str) + " :: " + \
        analysis_df["Impuls"].apply(norm_impuls)
    return bool(key.duplicated().any())


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


def teacher_in_transcript(transcript_text, teacher_name) -> bool:
    """True, wenn die Lehrkraft im Transkript als Sprecher auftaucht.

    Prüfung vor einer Lehrkraft-Analyse: erst als Sprecherlabel am Zeilen-
    anfang ("Name:"), sonst als schlichter Substring-Fallback. Leerer Name
    oder leeres Transkript → False.
    """
    if not teacher_name or not transcript_text:
        return False
    pattern = re.compile(r"^\s*" + re.escape(teacher_name) + r"\s*:",
                         re.IGNORECASE | re.MULTILINE)
    if pattern.search(transcript_text):
        return True
    return teacher_name.lower() in transcript_text.lower()


def filter_second_pass_items(df2, pending, teacher_name):
    """Nachcodierte Items behalten, die einem vorgelegten Turn entsprechen.

    Sicherheitsnetz der zweiten Prüfrunde: das Modell darf ausschließlich die
    gelisteten (uncodierten) Turns nachcodieren. Matching wie der Ergebnis-
    Merge (norm_impuls + Lehrkraft-Aliasse); Sprecherlabels werden auf den
    Lehrkraft-Namen kanonisiert. NaN-Konfidenz (Spalte existiert, Wert fehlt)
    wird nicht verschleppt. Gibt die akzeptierten Item-Dicts zurück.
    """
    if df2 is None or df2.empty:
        return []
    teacher_name = str(teacher_name or "")
    aliases = _TEACHER_ALIAS_BASE | {teacher_name.lower()}
    allowed = {f"{spk} :: {norm_impuls(utt)}" for spk, utt in pending}
    new_items = []
    for it in df2.to_dict("records"):
        spk = str(it.get("Sprecher", ""))
        spk_c = teacher_name if spk.lower() in aliases else spk
        if f"{spk_c} :: {norm_impuls(it.get('Impuls', ''))}" not in allowed:
            continue
        konf = it.get("Konfidenz")
        if konf is None or (isinstance(konf, float) and pd.isna(konf)):
            it.pop("Konfidenz", None)
        new_items.append(it)
    return new_items


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
        if "Konfidenz" in analysis_df.columns:
            analysis_df["Shortcode"] = _with_confidence(
                analysis_df["Shortcode"], analysis_df["Konfidenz"])
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
    # Single-Coding: die eine überlebende Code-Zelle trägt jetzt ebenfalls die
    # Konfidenz (falls das Modell eine geliefert hat) — "CODE (NN %)".
    if "Konfidenz" in coded.columns:
        coded["Shortcode"] = _with_confidence(coded["Shortcode"], coded["Konfidenz"])
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


def build_qual_plot(merged_df, t, mode="light", teacher_name=None):
    """Balkenplot der Code-Häufigkeiten, gestapelt nach Sprechergruppe.

    Ein Balken pro Code; die Gesamthöhe bleibt die Gesamthäufigkeit (wie vor
    der Aufteilung), zweifarbig geteilt in Lehrkraft- und Schüler:innen-
    Anteil. So bleibt "wie häufig" lesbar und "von wem" kommt dazu — das ist
    der Interaktions-Aspekt, den die reine Gesamtverteilung verdeckt.
    Ohne `teacher_name` (oder ohne Sprecher-Spalte) fällt der Plot auf die
    einfarbige Gesamtdarstellung zurück. Gibt immer ein matplotlib-Axes
    zurück. Gezählt wird nur der PRIMÄRcode — siehe primary_code_series.
    """
    if merged_df is None or merged_df.empty:
        return _no_data_axes(t, mode)
    counts = code_counts_by_group(merged_df, t, teacher_name)
    if counts.empty:
        return _no_data_axes(t, mode)

    teacher_label = t("report", "teacher")
    pupils_label = t("report", "pupils")
    split = bool(counts[teacher_label].any() and counts[pupils_label].any())
    # Eigene Figure statt der aktuellen Achse (gca): sonst zeichnet ein
    # zweiter Aufruf in denselben Axes und die Balken stapeln sich auf.
    _, ax = plt.subplots()
    if split:
        analysis_plot = counts.plot(
            ax=ax, kind="bar", stacked=True, alpha=1, rot=0, width=0.55,
            color=[primary_color(mode), secondary_color(mode)],
        )
    else:
        # Nur eine Sprechergruppe codiert: Stapel + Legende wären irreführend
        # (eine Farbe, ein toter Legendeneintrag) — dann die klassische
        # einfarbige Darstellung der Gesamtsumme.
        total = counts.sum(axis=1).rename(t("report", "quantity"))
        analysis_plot = total.plot(
            ax=ax, kind="bar", alpha=1, rot=0, width=0.55,
            color=primary_color(mode),
        )
    analysis_plot.set_xlabel(t("report", "shortcode"))
    plt.setp(analysis_plot.get_xticklabels(), rotation=45, ha="right")
    analysis_plot.set_ylabel(t("report", "quantity"))
    legend = analysis_plot.get_legend()
    if legend is not None:
        if split:
            legend.set_title(None)
        else:
            legend.remove()
    for container in analysis_plot.containers:
        # Beim Stapel nur Segmente > 0 beschriften, sonst überlagern sich
        # "0"-Labels mit den Nachbarsegmenten.
        labels = [int(v) if v else "" for v in container.datavalues]
        analysis_plot.bar_label(
            container, labels=labels,
            label_type="center" if split else "edge",
        )
    round_bar_corners(analysis_plot)
    apply_axes_style(analysis_plot, mode)
    return analysis_plot


def _no_data_axes(t, mode):
    """Leeres Axes mit "keine Daten"-Hinweis (Plot-Helfer)."""
    _, ax = plt.subplots()
    ax.text(0.5, 0.5, t("results", "no_data"),
            ha="center", va="center", fontsize=12)
    ax.axis("off")
    style_no_data_axes(ax, mode)
    return ax


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
