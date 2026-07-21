from shiny import ui
from faicons import icon_svg


def build_sidebar():
    return ui.sidebar(
        ui.input_action_button("language_toggle", "English", icon=icon_svg("globe")),
        # Report download sits up top so it is hard to miss. Direct sidebar
        # child (no wrapper) so it aligns with the buttons below; the render
        # slot keeps its id and returns None until a report is ready.
        ui.output_ui("show_report_download_button"),
        # Organisation only — LLM configuration moved to the Analysis tab.
        ui.output_ui("loc_button_import_session"),
        ui.output_ui("loc_button_export_session"),
        ui.output_ui("loc_button_history"),
        ui.output_ui("loc_button_reset"),
    )
