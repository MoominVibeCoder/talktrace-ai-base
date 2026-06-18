"""Tests for the Feedback tab pure logic (no network / no LLM call)."""
import pandas as pd
import pytest

from talktrace_ai.utils import feedback_section as fb
from talktrace_ai.utils.llm_analysis._freeform import chat_completion


# --- fixtures --------------------------------------------------------

def _stats_df():
    """Shape of a dialog_stats() result: teacher row + aggregate students row."""
    return pd.DataFrame(
        [
            {"Sprecher": "LEHRER", "Anzahl_Beitraege": 9, "Gesamt_Woerter": 120,
             "Durchschnitt_Woerter": 13.3, "Median_Woerter": 11},
            {"Sprecher": "Schüler:innen", "Anzahl_Beitraege": 15, "Gesamt_Woerter": 180,
             "Durchschnitt_Woerter": 12.0, "Median_Woerter": 10},
        ]
    )


def _analysis_df():
    rows = [
        ("LEHRER", "L"), ("LEHRER", "EN"), ("LEHRER", "EI"), ("LEHRER", "H"),
        ("LEHRER", "V"), ("LEHRER", "ZK"), ("LEHRER", "R"), ("LEHRER", "I"),
        ("S01", "N"),  # student row — must NOT be counted in the teacher profile
    ]
    return pd.DataFrame(
        [{"#": i, "Sprecher": s, "Shortcode": c, "Impuls": f"u{i}"}
         for i, (s, c) in enumerate(rows, 1)],
        columns=["#", "Sprecher", "Shortcode", "Impuls"],
    )


def _codebook():
    return [
        {"Code": "L", "Bezeichnung": "Gespräch leiten", "Beschreibung": "Steuert."},
        {"Code": "EN", "Bezeichnung": "Ermutigen zum Nachdenken", "Beschreibung": "Fragt nach Begründung."},
    ]


# --- build_metrics ---------------------------------------------------

def test_build_metrics_computes_talk_share():
    m = fb.build_metrics(_stats_df(), num_participants=6, participation_rate=27.3,
                         num_pupils=22, teacher_name="LEHRER")
    assert m["teacher_turns"] == 9
    assert m["student_turns"] == 15
    assert m["total_words"] == 300
    assert m["teacher_talk_share"] == 40.0  # 120 / 300
    assert m["num_participants"] == 6
    assert m["num_pupils"] == 22


def test_build_metrics_handles_none_and_empty():
    for df in (None, pd.DataFrame()):
        m = fb.build_metrics(df, teacher_name="LEHRER")
        assert m["teacher_turns"] == 0
        assert m["teacher_talk_share"] == 0


# --- extract_code_definitions ----------------------------------------

def test_extract_code_definitions_de_and_passthrough():
    defs = fb.extract_code_definitions(_codebook())
    codes = [c for c, _, _ in defs]
    assert codes == ["L", "EN"]
    assert defs[0][1] == "Gespräch leiten"
    assert "Steuert" in defs[0][2]


def test_extract_code_definitions_bad_input():
    assert fb.extract_code_definitions("not a list") == []
    assert fb.extract_code_definitions(None) == []


# --- teacher_code_profile --------------------------------------------

def test_teacher_code_profile_counts_teacher_only():
    prof = fb.teacher_code_profile(_analysis_df(), teacher_name="LEHRER")
    assert prof.get("L") == 1
    assert prof.get("EN") == 1
    assert "N" not in prof  # the S01 student row is excluded


def test_teacher_code_profile_empty_df():
    assert fb.teacher_code_profile(None, "LEHRER") == {}
    assert fb.teacher_code_profile(pd.DataFrame(), "LEHRER") == {}


# --- build_feedback_prompts ------------------------------------------

@pytest.mark.parametrize("lang", ["de", "en"])
def test_build_feedback_prompts_basic(lang):
    m = fb.build_metrics(_stats_df(), num_participants=6, participation_rate=27.3,
                         num_pupils=22, teacher_name="LEHRER")
    defs = fb.extract_code_definitions(_codebook())
    profile = fb.teacher_code_profile(_analysis_df(), "LEHRER")
    sys_p, usr_p = fb.build_feedback_prompts(
        lang=lang, model="gpt-x", metrics=m, code_definitions=defs, code_profile=profile,
    )
    assert isinstance(sys_p, str) and isinstance(usr_p, str)
    # metrics + code ids surface in the user prompt
    assert "40.0" in usr_p          # talk share
    assert "EN" in usr_p
    # the fixed reference list is injected, never invented
    assert "Alexander" in usr_p and "T-SEDA" in usr_p
    # the four section headings appear in the system prompt
    heads = fb.FEEDBACK_HEADINGS[lang]
    for key in ("strengths", "development", "tips", "sources"):
        assert heads[key] in sys_p


def test_build_feedback_prompts_langs_differ():
    de_sys, _ = fb.build_feedback_prompts(lang="de")
    en_sys, _ = fb.build_feedback_prompts(lang="en")
    assert de_sys != en_sys


def test_build_feedback_prompts_handles_empty_inputs():
    # No metrics / codes / profile must not raise.
    sys_p, usr_p = fb.build_feedback_prompts(lang="de")
    assert "Stärken" in sys_p
    assert isinstance(usr_p, str) and usr_p


def test_codes_block_keeps_description_without_label():
    # A codebook entry with a description but no label must not lose the text.
    _, usr_p = fb.build_feedback_prompts(
        lang="de", code_definitions=[("R2", "", "explizite Begruendung")],
    )
    assert "explizite Begruendung" in usr_p


def test_num_handles_non_finite_floats():
    assert fb._num(float("inf")) == 0
    assert fb._num(float("-inf")) == 0
    assert fb._num(float("nan")) == 0
    assert fb._num(3) == 3
    assert fb._num(2.5) == 2.5


# --- clean_markdown --------------------------------------------------

def test_clean_markdown_strips_syntax():
    md = (
        "## Stärken\n"
        "Sie nutzen **offene Fragen** und *Wartezeit*.\n"
        "* erster Punkt\n"
        "+ zweiter Punkt\n"
        "> ein Zitat\n"
    )
    out = fb.clean_markdown(md)
    assert "#" not in out
    assert "**" not in out
    assert "Stärken" in out
    assert "offene Fragen" in out and "Wartezeit" in out
    # markdown bullets normalized to a plain hyphen, blockquote marker gone
    assert "- erster Punkt" in out
    assert "- zweiter Punkt" in out
    assert "> ein Zitat" not in out and "ein Zitat" in out


def test_clean_markdown_handles_empty():
    assert fb.clean_markdown("") == ""
    assert fb.clean_markdown(None) == ""


# --- write_feedback_docx ---------------------------------------------

def test_write_feedback_docx_roundtrip(tmp_path):
    from docx import Document

    text = (
        "## Stärken\nSie stellen viele offene Fragen.\n\n"
        "## Entwicklungsfelder\n- Mehr Wartezeit geben.\n\n"
        "## Konkrete Umsetzungstipps\nNutzen Sie Think-Pair-Share.\n\n"
        "## Quellen\n- Alexander, R. J. (2020).\n"
    )
    fp = tmp_path / "feedback.docx"
    fb.write_feedback_docx(str(fp), text, lang="de",
                           doc_title="Unterrichts-Feedback", disclaimer="Reflexionshilfe.")
    assert fp.stat().st_size > 3000
    doc = Document(str(fp))
    body = "\n".join(p.text for p in doc.paragraphs)
    assert "Wartezeit" in body
    assert "Reflexionshilfe" in body          # disclaimer footer present
    assert "Think-Pair-Share" in body


# --- chat_completion (no network) ------------------------------------

def test_chat_completion_rejects_unknown_provider():
    with pytest.raises(ValueError):
        chat_completion("acme", "m", "sys", "usr", "key")


def test_chat_completion_missing_key_raises_runtime():
    with pytest.raises(RuntimeError):
        chat_completion("openai", "gpt-x", "sys", "usr", "")
