"""Consent tab: a GDPR Art. 13 consent-declaration generator.

Pre-filled with the TalkTrace training-context defaults (local
transcription, the configured LLM provider as recipient / possible
third-country transfer, withdrawal + data-subject rights). The trainer
fills in the responsible party, tweaks the text, previews the document
and downloads a standalone HTML file to print per teacher.

Text adapted from the CC0 "Consent-Gen-RDMO" (TU Dortmund). See
``talktrace_ai/consent.py`` for the pure rendering logic.
"""
from ._common import *
from .. import consent as consent_mod


def register(state):
    input = state.input
    output = state.output
    config = state.config
    t = state.t
    current_lang = state.current_lang

    # Last generated document (inner HTML+style); None until first preview.
    consent_preview_html = reactive.value(None)

    def _S():
        """Current-language 'consent' localization section."""
        return TRANSLATIONS[current_lang.get()]["consent"]

    def _collect():
        """Read the form inputs into a plain data dict (consent_mod.FIELDS)."""
        def g(name, default=""):
            try:
                v = getattr(input, f"consent_{name}")()
            except Exception:
                v = None
            return v if v is not None else default
        return {f: g(f) for f in consent_mod.FIELDS}

    # ------------------------------------------------------------------
    # Localized titles
    # ------------------------------------------------------------------
    @render.text
    def loc_title_consent():
        return t("consent", "tab_title")

    @render.ui
    def consent_section_title():
        return ui.span(icon_svg("file-signature"), " ", t("consent", "section_title"))

    # ------------------------------------------------------------------
    # Main section: form (left) + live preview (right)
    # ------------------------------------------------------------------
    @render.ui
    def consent_section():
        api = config.get_current_api()
        mode_default = consent_mod.default_llm_mode(api)

        def ta(name, rows=2):
            return ui.input_text_area(
                f"consent_{name}", t("consent", f"field_{name}"),
                value=t("consent", f"default_{name}") if _has_default(name) else "",
                placeholder=t("consent", f"ph_{name}") if _has_ph(name) else "",
                rows=rows, width="100%",
            )

        def tx(name):
            return ui.input_text(
                f"consent_{name}", t("consent", f"field_{name}"),
                value=t("consent", f"default_{name}") if _has_default(name) else "",
                placeholder=t("consent", f"ph_{name}") if _has_ph(name) else "",
                width="100%",
            )

        form = ui.div(
            ui.p(t("consent", "intro_hint")),
            ui.div(
                icon_svg("circle-info"), " ", t("consent", "disclaimer"),
                class_="alert alert-warning py-2 px-3", role="alert",
                style="font-size: 0.9rem;",
            ),
            tx("project_name"),
            ta("responsible", rows=3),
            ta("dpo", rows=2),
            ta("purpose", rows=2),
            tx("legal_basis"),
            ta("data_categories", rows=2),
            # LLM recipient: mode toggle drives whether a third-country
            # transfer paragraph and a separate consent checkbox appear.
            ui.input_radio_buttons(
                "consent_llm_mode", t("consent", "field_llm_mode"),
                choices={
                    "cloud": t("consent", "field_llm_mode_cloud"),
                    "local": t("consent", "field_llm_mode_local"),
                },
                selected=mode_default,
            ),
            ui.output_ui("consent_provider_field"),
            tx("storage"),
            ta("revocation", rows=2),
            ta("authority", rows=2),
            ui.hr(),
            ui.tags.h6(t("consent", "per_participant_heading")),
            tx("participant_name"),
            tx("place_date"),
            ui.div(
                ui.input_action_button(
                    "consent_generate", t("consent", "generate_button"),
                    icon=icon_svg("wand-magic-sparkles"), class_="btn-primary",
                ),
                ui.download_button(
                    "consent_download", t("consent", "download_button"),
                    icon=icon_svg("download"), class_="btn-success",
                ),
                style="display:flex; gap:0.6rem; margin-top:0.75rem; flex-wrap:wrap;",
            ),
        )

        preview = ui.div(
            ui.output_ui("consent_preview"),
            style=("border:1px solid var(--bs-border-color); border-radius:0.5rem; "
                   "background:#fff; padding:0.5rem; max-height:75vh; overflow:auto;"),
        )

        return ui.layout_columns(form, preview, col_widths=[5, 7])

    # Provider text field — shown only in cloud mode.
    @render.ui
    def consent_provider_field():
        try:
            mode = input.consent_llm_mode()
        except Exception:
            mode = "cloud"
        if mode != "cloud":
            return None
        prov_default = consent_mod.default_provider_label(config.get_current_api())
        return ui.input_text(
            "consent_llm_provider", t("consent", "field_llm_provider"),
            value=prov_default, placeholder=t("consent", "ph_llm_provider"),
            width="100%",
        )

    # ------------------------------------------------------------------
    # Preview rendering
    # ------------------------------------------------------------------
    @render.ui
    def consent_preview():
        html_doc = consent_preview_html.get()
        if not html_doc:
            return ui.div(
                ui.p(t("consent", "preview_empty"),
                     style="color:#888; text-align:center; padding:2rem 1rem;"),
            )
        return ui.HTML(html_doc)

    @reactive.effect
    @reactive.event(input.consent_generate)
    def _generate():
        data = _collect()
        consent_preview_html.set(consent_mod.build_consent_preview(data, _S()))

    # ------------------------------------------------------------------
    # Download: standalone, print-ready HTML
    # ------------------------------------------------------------------
    def _download_name():
        with reactive.isolate():
            data = _collect()
        who = (data.get("participant_name") or "").strip()
        stem = "Einwilligung"
        if who:
            safe = re.sub(r"[^\w\-]+", "_", who).strip("_")
            if safe:
                stem = f"Einwilligung_{safe}"
        return f"{stem}.html"

    @render.download(filename=_download_name)
    def consent_download():
        with reactive.isolate():
            data = _collect()
            S = _S()
        yield consent_mod.build_consent_standalone(data, S).encode("utf-8")


# Localization keys that have a default_<name> / ph_<name> entry. Kept as
# module-level sets so the form builder can decide whether to prefill.
_DEFAULT_FIELDS = {
    "project_name", "purpose", "legal_basis", "data_categories", "storage",
}
_PH_FIELDS = {
    "responsible", "dpo", "revocation", "authority",
    "participant_name", "place_date", "llm_provider",
}


def _has_default(name):
    return name in _DEFAULT_FIELDS


def _has_ph(name):
    return name in _PH_FIELDS
