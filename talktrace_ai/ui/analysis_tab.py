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
        # Row 1.5: optional local audio transcription (noScribe engine).
        # Collapsed by default — it produces what the transcript input below
        # consumes, so it sits directly above it. Hidden behind an accordion
        # to avoid cluttering the default upload-an-existing-transcript flow.
        ui.accordion(
            ui.accordion_panel(
                ui.output_ui("noscribe_section_title"),
                ui.output_ui("noscribe_section"),
                value="noscribe",
            ),
            id="noscribe_accordion",
            open=False,
        ),
        # Row 2: Document Input — 2 columns (transcript left, codebook right)
        ui.card(
            ui.card_header(ui.output_ui("loc_document_input")),
            ui.layout_columns(
                ui.output_ui("loc_upload_transcript"),
                ui.output_ui("loc_upload_codebook"),
            ),
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
