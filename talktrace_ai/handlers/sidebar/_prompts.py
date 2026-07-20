"""LLM/speaker switches + prompt sanitization + effective prompt reactives.

Exposes ``state.effective_system_prompt``, ``state.effective_user_prompt``,
and ``state._speaker_flags`` so cost prediction and analysis can read them.
"""
from .._common import *


def register(state):
    input = state.input
    output = state.output
    t = state.t
    system_prompt = state.system_prompt
    user_prompt = state.user_prompt

    # LLM Analyse. suspend_when_hidden=False: this slot MOUNTS llm_switch,
    # which the quick-start checklist, cost prediction and the demo loader's
    # update_switch read from any tab — it must exist from session start
    # (as it did when it lived in the always-visible sidebar), not only
    # after the Analysis tab was first opened.
    @output(suspend_when_hidden=False)
    @render.ui
    def loc_llm_switch():
        return ui.div(
            ui.input_switch("llm_switch", t("sidebar", "llm_switch"), True),
            class_="ttai-switch-compact",
            **{"data-tt-help": t("onboarding", "tooltip_llm_switch")},
        )

    # Seed-Werte für die Sprechakt-Switches. Der render.ui-Slot unten wird
    # bei jedem llm_switch-Toggle neu gerendert und setzt die Switches auf
    # diese Startwerte zurück. Vorlagen-Loader (z. B. T-SEDA) schreiben ihre
    # Pre-Sets HIER hinein und rufen zusätzlich update_switch: sind die
    # Switches gerade gemountet, greift das Update sofort; sind sie es nicht
    # (llm_switch war aus), rendert der Slot beim Einschalten mit den
    # Seed-Werten. Bewusst ein plain dict — kein reactive.value, sonst würde
    # jede Seed-Änderung ein Re-Render (und damit einen Werte-Reset) auslösen.
    _switch_seed = {"teacher": True, "students": True, "multi": False}
    state.speaker_switch_seed = _switch_seed

    # Sprechakt-Auswahl: nur sichtbar, wenn LLM-Analyse aktiv ist. Same
    # non-suspend rationale: the speaker/multi-coding switches feed the
    # effective prompts, which reports and the Options preview read from
    # any tab.
    @output(suspend_when_hidden=False)
    @render.ui
    def loc_analyse_speakers_switches():
        if not input.llm_switch():
            return None
        return ui.div(
            ui.input_switch("analyse_teacher_switch", t("sidebar", "analyse_teacher_switch"), _switch_seed["teacher"]),
            ui.input_switch("analyse_students_switch", t("sidebar", "analyse_students_switch"), _switch_seed["students"]),
            ui.input_switch("multi_coding_switch", t("sidebar", "multi_coding_switch"), _switch_seed["multi"]),
            class_="ttai-switch-compact",
        )

    # Effektive Prompts: Basis-Prompt + Zusatzanweisung je nach Sprecher-Auswahl.
    # Wird sowohl in der Options-Anzeige als auch beim LLM-Call verwendet,
    # damit der User sieht, was tatsächlich ans Modell geschickt wird.
    def _speaker_flags():
        # Switches werden nur gerendert, wenn llm_switch aktiv ist;
        # fallback auf True (Default), solange sie nicht existieren.
        try:
            teacher = bool(input.analyse_teacher_switch())
        except Exception:
            teacher = True
        try:
            students = bool(input.analyse_students_switch())
        except Exception:
            students = True
        return teacher, students

    def _multi_coding_flag() -> bool:
        """Schalter-Wert defensiv lesen — der Switch wird nur gerendert,
        solange ``llm_switch`` aktiv ist. Default OFF.
        """
        try:
            return bool(input.multi_coding_switch())
        except Exception:
            return False

    def _multi_coding_suffix(kind: str = "system") -> str:
        """Liefert den Prompt-Zusatz, der dem LLM mitteilt, ob Mehrfach-
        Codierung erlaubt/erwünscht (ON) oder verboten (OFF) ist. Wird
        sowohl an System- als auch an User-Prompt angehängt, damit das
        Modell unmissverständlich weiß, was es tun soll. Post-Processing
        (Hierarchie + drop_duplicates / groupby) bleibt als Sicherheitsnetz."""
        prefix = "user_prompt_multi_coding" if kind == "user" else "prompt_multi_coding"
        key = f"{prefix}_{'on' if _multi_coding_flag() else 'off'}"
        return t("sidebar", key)

    def _context_suffix(kind: str = "system") -> str:
        """Anweisung, jeden Turn im Licht des Gesprächsverlaufs zu codieren
        (statt isoliert). Immer aktiv — Dialog-Codes wie „auf Ideen
        aufbauen" oder „herausfordern" sind ohne den vorangehenden Turn
        oft gar nicht erkennbar. Das LLM sieht ohnehin das komplette
        Transkript; dieser Suffix macht die Nutzung des Kontexts explizit."""
        key = "user_prompt_context" if kind == "user" else "prompt_context"
        return t("sidebar", key)

    def _relevance_suffix(kind: str = "system") -> str:
        """Anweisung, Nicht-Züge uncodiert zu lassen: bloßes Drannehmen,
        Minimal-Feedback ohne eigenen Inhalt („Ja.", „Genau."), Unverständ-
        liches („(unv.)"). Immer aktiv und bewusst CODE-unabhängig in der
        Prompt-Schicht: die Drannehmen-Regel stand zuvor nur in einzelnen
        Codebuch-Einträgen (L/ÄN) — Modelle griffen dann zu einem Code, in
        dessen Eintrag die Regel nicht stand (EN, 90 % Konfidenz). Die
        Kontext-Ausnahme bleibt: ein „Nein." als Widerspruch oder eine
        knappe Sachantwort SIND codierbare Züge."""
        key = "user_prompt_relevance" if kind == "user" else "prompt_relevance"
        return t("sidebar", key)

    def _speaker_filter_suffix(kind: str = "system"):
        teacher, students = _speaker_flags()
        prefix = "user_prompt_filter" if kind == "user" else "prompt_filter"
        if teacher and students:
            return ""
        # Read the input only past the early return: in the default case the
        # suffix must not depend on (and silently fail with) an input that may
        # not be mounted yet.
        try:
            teacher_name = input.name_teacher() or t("analysis", "name_teacher_var")
        except Exception:
            teacher_name = t("analysis", "name_teacher_var")
        if teacher and not students:
            return t("sidebar", f"{prefix}_teacher_only").format(teacher_name=teacher_name)
        if students and not teacher:
            return t("sidebar", f"{prefix}_students_only").format(teacher_name=teacher_name)
        return t("sidebar", f"{prefix}_none")

    def _sanitize_prompt_for_speakers(text: str, teacher: bool, students: bool) -> str:
        """Remove teacher/student references from prompt text when that group is disabled.
        Keeps the text grammatical for the default prompts; custom prompts are
        handled best-effort."""
        if teacher and students:
            return text
        # --- German references -------------------------------------------------
        if not teacher:
            text = text.replace("Lehrperson UND Schüler:innen", "Schüler:innen")
            text = text.replace("Lehrperson und Schüler:innen", "Schüler:innen")
            text = text.replace("ALLER Sprecher:innen (Lehrperson UND Schüler:innen)", "der Schüler:innen")
            text = text.replace("ALLER Sprecher:innen", "der Schüler:innen")
            text = text.replace("Lehrperson", "")
            text = text.replace("LEHRER", "")
            text = text.replace("Lehrer", "")
        if not students:
            text = text.replace("Lehrperson UND Schüler:innen", "Lehrperson")
            text = text.replace("Lehrperson und Schüler:innen", "Lehrperson")
            text = text.replace("ALLER Sprecher:innen (Lehrperson UND Schüler:innen)", "der Lehrperson")
            text = text.replace("ALLER Sprecher:innen", "der Lehrperson")
            text = text.replace("Schüler:innen", "")
            text = text.replace("S01, S02, S03…", "")
            text = text.replace("S01, S02, S03...", "")
            text = text.replace("S01, S02, S03", "")
            text = text.replace("S01", "")
        # --- English references ------------------------------------------------
        if not teacher:
            text = text.replace("teacher AND students", "students")
            text = text.replace("teacher and students", "students")
            text = text.replace("ALL speakers (teacher AND students)", "students")
            text = text.replace("ALL speakers", "students")
            text = text.replace("teacher", "")
        if not students:
            text = text.replace("teacher AND students", "teacher")
            text = text.replace("teacher and students", "teacher")
            text = text.replace("ALL speakers (teacher AND students)", "teacher")
            text = text.replace("ALL speakers", "teacher")
            text = text.replace("students", "")
            text = text.replace("S01, S02, S03…", "")
            text = text.replace("S01, S02, S03...", "")
            text = text.replace("S01, S02, S03", "")
            text = text.replace("S01", "")
        # --- Cleanup whitespace artifacts --------------------------------------
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s*-\s*", "-", text)
        return text.strip()

    @reactive.calc
    def effective_system_prompt():
        teacher, students = _speaker_flags()
        base = _sanitize_prompt_for_speakers(system_prompt.get(), teacher, students)
        return (base + _speaker_filter_suffix("system")
                + _context_suffix("system") + _relevance_suffix("system")
                + _multi_coding_suffix("system"))

    @reactive.calc
    def effective_user_prompt():
        teacher, students = _speaker_flags()
        raw = _sanitize_prompt_for_speakers(user_prompt.get(), teacher, students)
        # Alle Instruktions-Suffixe (Sprecher-Filter + Kontext + Relevanz +
        # Multi-Coding) werden gemeinsam direkt nach dem {transcript}-Block
        # platziert. Hintergrund: LLMs leiden bei sehr langen Kontexten unter
        # "lost in the middle" — Anweisungen über Output-Format und Filter
        # müssen nahe am Transkript sitzen, nicht am Ende nach tausenden
        # Token Codebook.
        combined = (_speaker_filter_suffix("user")
                    + _context_suffix("user") + _relevance_suffix("user")
                    + _multi_coding_suffix("user"))
        if not combined:
            return raw
        if "{transcript}" in raw:
            target = "{transcript}"
            idx = raw.index(target)
            insert_pos = idx + len(target)
            return raw[:insert_pos] + "\n\n" + combined + raw[insert_pos:]
        return raw + combined

    state.effective_system_prompt = effective_system_prompt
    state.effective_user_prompt = effective_user_prompt
    state._speaker_flags = _speaker_flags
