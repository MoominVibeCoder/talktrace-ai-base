from shiny import ui
from faicons import icon_svg


def build_feedback_tab():
    """Dedicated tab hosting the LLM-generated teacher feedback.

    The whole body is rendered by handlers/feedback.py: a generate button that
    produces formative, research-grounded feedback from the analysis results
    (T-SEDA teacher-code profile + quantitative metrics), shown in an editable
    field, plus DOCX/PDF download. Requires an analysis with LLM coding first.
    """
    return ui.nav_panel(
        ui.output_text("loc_title_feedback"),
        ui.card(
            ui.card_header(ui.output_ui("feedback_section_title")),
            ui.output_ui("feedback_section"),
        ),
        icon=icon_svg("comments"),
    )
