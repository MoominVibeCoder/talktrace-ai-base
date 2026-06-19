from shiny import ui
from faicons import icon_svg


def build_start_tab():
    """Landing tab shown on launch.

    The whole body is rendered by handlers/start.py: a short intro, a workflow
    status strip (Audio → Transcript → Analysis → Feedback → Export), entry
    tiles into the other tabs, the current LLM-configuration line, a "what's
    new" card, and (from phase 6) the data-protection acknowledgment that
    gates LLM calls. All content is read from AppState; this tab owns no
    cross-handler state.

    Phase 2 ships an inert shell (title + intro placeholder); later phases
    fill in the interactive content.
    """
    return ui.nav_panel(
        ui.output_text("loc_title_start"),
        ui.output_ui("start_section"),
        icon=icon_svg("house"),
    )
