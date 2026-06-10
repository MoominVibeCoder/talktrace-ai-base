from shiny import ui
from faicons import icon_svg


def build_consent_tab():
    """Dedicated tab hosting the GDPR consent-declaration generator.

    The whole body is rendered by handlers/consent.py: a pre-filled form
    on the left, a live print-ready preview on the right, plus a download
    button for a standalone HTML document the trainer prints to PDF.
    """
    return ui.nav_panel(
        ui.output_text("loc_title_consent"),
        ui.card(
            ui.card_header(ui.output_ui("consent_section_title")),
            ui.output_ui("consent_section"),
        ),
        icon=icon_svg("file-signature"),
    )
