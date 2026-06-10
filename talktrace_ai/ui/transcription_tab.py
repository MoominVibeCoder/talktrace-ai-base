from shiny import ui
from faicons import icon_svg


def build_transcription_tab():
    """Dedicated tab hosting the local noScribe transcription engine.

    The whole body is a single status-driven output (`noscribe_section`)
    rendered by handlers/noscribe.py — install prompt, full options form,
    or live progress depending on engine state.
    """
    return ui.nav_panel(
        ui.output_text("loc_title_transcription"),
        ui.card(
            ui.card_header(ui.output_ui("noscribe_section_title")),
            ui.output_ui("noscribe_section"),
        ),
        icon=icon_svg("microphone"),
    )
