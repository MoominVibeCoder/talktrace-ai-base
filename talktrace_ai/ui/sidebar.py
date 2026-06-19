from shiny import ui
from faicons import icon_svg


def build_sidebar():
    return ui.sidebar(
        ui.input_action_button("language_toggle", "English", icon=icon_svg("globe")),
        # Organisation only — LLM configuration moved to the Analysis tab and
        # the report download to the Results tab (redesign 2026).
        ui.output_ui("loc_button_import_session"),
        ui.output_ui("loc_button_export_session"),
        ui.output_ui("loc_button_history"),
        ui.output_ui("loc_button_reset"),
    )
