from shiny import ui
from faicons import icon_svg


def build_analysis_tab():
    return ui.nav_panel(
        ui.output_text("loc_title_analysis"),
        # Row 1: General Info — full width, fields side by side
        ui.card(
            ui.card_header(ui.output_ui("loc_general_info")),
            ui.layout_columns(
                ui.output_ui("loc_group_id"),
                ui.output_ui("loc_num_pupils"),
                ui.output_ui("loc_name_teacher"),
            ),
        ),
        # Row 2: Document Input — 2 columns (transcript left, codebook right)
        ui.card(
            ui.card_header(ui.output_ui("loc_document_input")),
            ui.layout_columns(
                ui.output_ui("loc_upload_transcript"),
                ui.output_ui("loc_upload_codebook"),
            ),
        ),
        # Row 2b: LLM configuration — the model picker, switches, cost chip
        # and analyse/cancel buttons live here (moved out of the sidebar).
        # The output_ui slots keep their original ids, so all reactive
        # handlers in handlers/sidebar/* drive them unchanged.
        ui.card(
            ui.card_header(ui.output_ui("loc_llm_config_title")),
            ui.layout_columns(
                ui.div(
                    ui.output_ui("loc_dynamic_model_select"),
                    ui.output_ui("loc_provider_hint"),
                ),
                ui.div(
                    ui.output_ui("loc_llm_switch"),
                    ui.output_ui("loc_analyse_speakers_switches"),
                ),
            ),
            ui.div(
                ui.output_ui("cost_chip"),
                ui.output_ui("loc_button_analysis"),
                ui.output_ui("loc_button_cancel_analysis"),
                class_="d-flex align-items-center flex-wrap gap-2 mt-2",
            ),
            ui.output_ui("start_analysis"),
        ),
        # Row 3: Previews — 2 columns matching upload order
        ui.layout_columns(
            ui.card(
                ui.card_header(ui.output_ui("loc_general_transcript")),
                ui.output_ui("show_transcript_preview"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header(ui.output_ui("loc_preview_codebook")),
                ui.output_ui("show_codebook_preview"),
                full_screen=True,
            ),
        ),
        icon=icon_svg("brain"),
    )
