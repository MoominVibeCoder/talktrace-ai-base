"""Tests for the consent-declaration generator (pure rendering logic)."""
import pytest

from talktrace_ai import consent as c
from talktrace_ai.localization.translation import TRANSLATIONS


@pytest.fixture(params=["de", "en"])
def S(request):
    return TRANSLATIONS[request.param]["consent"]


def _data(**kw):
    base = dict(
        project_name="Testfortbildung",
        responsible="TU Dortmund, Prof. X, x@uni.de",
        purpose="Reflexion",
        legal_basis="Art. 6(1)(a)",
        data_categories="Audio + Transkript",
        storage="1 Jahr",
        llm_mode="cloud",
        llm_provider="OpenAI, USA",
        revocation="widerruf@uni.de",
        authority="",
        participant_name="Maria Muster",
        place_date="Dortmund, 2026-06-10",
    )
    base.update(kw)
    return base


# --- provider/mode helpers -------------------------------------------

def test_default_provider_label_known_and_unknown():
    assert c.default_provider_label("openai") == "OpenAI, USA"
    assert c.default_provider_label("ollama") == ""        # local → empty
    assert c.default_provider_label("acme") == "acme"      # passthrough
    assert c.default_provider_label(None) == ""


def test_default_llm_mode():
    assert c.default_llm_mode("openai") == "cloud"
    assert c.default_llm_mode("ollama") == "local"
    assert c.default_llm_mode(None) == "cloud"


# --- HTML preview ----------------------------------------------------

def test_preview_contains_style_and_doc(S):
    html = c.build_consent_preview(_data(), S)
    assert "<style>" in html
    assert "ttai-consent-doc" in html
    assert "Testfortbildung" in html


def test_cloud_mode_mentions_provider(S):
    html = c.build_consent_preview(_data(llm_mode="cloud"), S)
    assert "OpenAI, USA" in html


def test_local_mode_hides_provider(S):
    html = c.build_consent_preview(_data(llm_mode="local"), S)
    assert "OpenAI, USA" not in html


def test_missing_required_field_marked(S):
    # build_consent_html has no <style> block (the CSS itself defines the
    # .ttai-missing class), so the marker check is unambiguous here.
    html = c.build_consent_html(_data(responsible=""), S)
    assert "ttai-missing" in html
    assert "!!!" in html


def test_filled_form_has_no_missing_markers(S):
    html = c.build_consent_html(_data(), S)
    assert "ttai-missing" not in html
    assert "!!!" not in html


def test_headings_forced_black_inline(S):
    # Inline !important keeps headings black inside the dark theme preview.
    html = c.build_consent_preview(_data(), S)
    assert 'color:#000 !important' in html


# --- standalone HTML -------------------------------------------------

def test_standalone_is_full_document(S):
    doc = c.build_consent_standalone(_data(), S)
    assert doc.startswith("<!DOCTYPE")
    assert "<html" in doc and "</html>" in doc


# --- DOCX ------------------------------------------------------------

def test_docx_roundtrip(tmp_path, S):
    from docx import Document

    fp = tmp_path / "consent.docx"
    c.write_consent_docx(str(fp), _data(responsible=""), S)
    assert fp.stat().st_size > 5000

    doc = Document(str(fp))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Testfortbildung" in text
    assert "OpenAI, USA" in text        # cloud recipient present
    assert "!!!" in text                # missing responsible flagged
