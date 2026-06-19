"""Start tab: the landing page shown on launch.

Composes a read-only overview of the app — intro, workflow status strip,
entry tiles, current LLM configuration, and "what's new" — plus (from phase 6)
the data-protection acknowledgment that gates LLM calls. All state is read
from AppState; this tab owns no cross-handler reactive values.

Phase 2 ships an inert shell (localized title + intro placeholder); later
phases wire the interactive content.
"""
from ._common import *


def register(state):
    t = state.t

    # ------------------------------------------------------------------
    # Localized tab title
    # ------------------------------------------------------------------
    @render.text
    def loc_title_start():
        return t("start", "tab_title")

    # ------------------------------------------------------------------
    # Main section (placeholder until phase 3)
    # ------------------------------------------------------------------
    @render.ui
    def start_section():
        return ui.div(
            ui.h2(t("start", "intro_headline")),
            ui.p(t("start", "intro_body"), class_="text-muted"),
            class_="p-2",
        )
