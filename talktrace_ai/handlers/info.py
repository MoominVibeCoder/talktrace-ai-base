"""Info tab: Entwickler, Lizenz, Banner."""
from ._common import *


def register(state):
    output = state.output
    t = state.t

    @render.text
    def loc_title_info():
        return t("info", "tab_title")

    @render.ui
    def loc_info_dev_heading():
        return ui.p(t("info", "dev_heading"))

    @render.ui
    def loc_info_dev_body():
        def _link(href, label):
            return ui.tags.a(label, href=href, target="_blank", rel="noopener noreferrer")

        return ui.div(
            ui.tags.h6(t("info", "dev_current"), " (TalkTrace AI base)"),
            ui.tags.p(
                _link("https://github.com/MoominVibeCoder", "Simon Filler"),
                " · ",
                _link("https://orcid.org/0009-0008-8736-8831", "ORCID"),
                " · ",
                _link("mailto:simon.filler@tu-dortmund.de", "simon.filler@tu-dortmund.de"),
            ),
            ui.tags.h6(
                t("info", "dev_origin"),
                " (",
                _link("https://github.com/talktrace-ai/talktrace-ai", "TalkTrace AI"),
                ")",
                style="margin-top:1rem;",
            ),
            ui.tags.p(
                _link(
                    "https://www.sozphil.uni-leipzig.de/institut-fuer-politikwissenschaft/arbeitsbereiche/professur-fuer-fachdidaktik-gemeinschaftskunde/team/prof-dr-dennis-hauk",
                    "Dennis Hauk",
                ),
                " · ",
                _link("https://orcid.org/0000-0002-5779-2876", "ORCID"),
                ui.tags.br(),
                _link("https://github.com/xrtze", "Jami Schorling"),
                " · ",
                _link("https://orcid.org/0009-0005-9007-2896", "ORCID"),
            ),
        )

    @render.ui
    def loc_info_transcription_heading():
        return ui.p(t("info", "transcription_heading"))

    @render.ui
    def loc_info_transcription_body():
        return ui.div(
            ui.tags.a(
                ui.tags.span(
                    "noScribe · GPL v3.0",
                    style="display:inline-block;border:1px solid currentColor;border-radius:0.25rem;padding:0.15rem 0.6rem;font-size:0.85rem;font-weight:600;margin-bottom:0.75rem;",
                ),
                href="https://github.com/kaixxx/noScribe",
                target="_blank",
                rel="noopener noreferrer",
                style="text-decoration:none;",
            ),
            ui.markdown(t("info", "transcription_text")),
        )

    @render.ui
    def loc_info_consent_heading():
        return ui.p(t("info", "consent_heading"))

    @render.ui
    def loc_info_consent_body():
        return ui.div(
            ui.tags.a(
                ui.tags.span(
                    "Consent-Gen-RDMO · CC0 1.0",
                    style="display:inline-block;border:1px solid currentColor;border-radius:0.25rem;padding:0.15rem 0.6rem;font-size:0.85rem;font-weight:600;margin-bottom:0.75rem;",
                ),
                href="https://github.com/berndzey/Consent-Gen-RDMO",
                target="_blank",
                rel="noopener noreferrer",
                style="text-decoration:none;",
            ),
            ui.markdown(t("info", "consent_text")),
        )

    @render.ui
    def loc_info_license_heading():
        return ui.p(t("info", "license_heading"))

    @render.ui
    def loc_info_license_body():
        return ui.div(
            ui.tags.a(
                ui.tags.span(
                    "AGPL v3.0",
                    style="display:inline-block;border:1px solid currentColor;border-radius:0.25rem;padding:0.15rem 0.6rem;font-size:0.85rem;font-weight:600;margin-bottom:0.75rem;",
                ),
                href="https://www.gnu.org/licenses/agpl-3.0.html",
                target="_blank",
                rel="noopener noreferrer",
                style="text-decoration:none;",
            ),
            ui.markdown(t("info", "license_text")),
        )
