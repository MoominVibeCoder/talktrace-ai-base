"""Start tab: the landing page shown on launch.

Read-only overview composed entirely from AppState: a short intro, a workflow
status strip (Audio → Transcript → Analysis → Feedback → Export), four entry
tiles into the other tabs, the current LLM-configuration line, and a "what's
new" card. The data-protection acknowledgment is wired in phase 6.

The four tiles reuse existing code paths rather than duplicating them: the
demo tile calls ``state.load_demo_session`` (published by handlers/onboarding)
and the resume tile calls ``state.show_history_modal`` (published by
handlers/sidebar/_session). Tab switches use ``ui.update_navset`` with the
rendered title markup, matching the convention used across the handlers.
"""
from ._common import *
from ..paths import _mark_dataprotection_acknowledged

# A nav_panel's value is the rendered markup of its title element (Shiny
# derives it when no explicit value= is given). Captured verbatim from the
# live DOM — keep in sync with the loc_title_* outputs in the tab builders.
_NAV_TRANSCRIPTION = '<div id="loc_title_transcription" class="shiny-text-output"></div>'
_NAV_ANALYSIS = '<div id="loc_title_analysis" class="shiny-text-output"></div>'

_PROVIDER_LABELS = {
    "openai": "OpenAI", "anthropic": "Anthropic",
    "mistral": "Mistral", "deepseek": "DeepSeek",
    "groq": "Groq", "ollama": "Ollama", "openrouter": "OpenRouter",
}


def register(state):
    input = state.input
    config = state.config
    t = state.t
    transcript_data = state.transcript_data
    analysis_state = state.analysis_state
    analysis_llm_state = state.analysis_llm_state
    model = state.model

    api_keys = {
        "groq": state.api_key_groq,
        "openai": state.api_key_openai,
        "anthropic": state.api_key_anthropic,
        "ollama": state.api_key_ollama,
        "openrouter": state.api_key_openrouter,
        "mistral": state.api_key_mistral,
        "deepseek": state.api_key_deepseek,
    }

    # ------------------------------------------------------------------
    # Localized tab title
    # ------------------------------------------------------------------
    @render.text
    def loc_title_start():
        return t("start", "tab_title")

    # ------------------------------------------------------------------
    # Building blocks (all read AppState — re-render on any change)
    # ------------------------------------------------------------------
    def _workflow_strip():
        present = transcript_data.get() is not None
        analysed = bool(analysis_state.get())
        llm_done = bool(analysis_llm_state.get())
        steps = [
            ("workflow_audio", present),
            ("workflow_transcript", present),
            ("workflow_analysis", analysed),
            ("workflow_feedback", llm_done),
            ("workflow_export", analysed),
        ]
        pills = []
        for i, (key, done) in enumerate(steps):
            status = t("start", "status_done") if done else t("start", "status_pending")
            mark = "✓" if done else "○"
            cls = "badge rounded-pill " + ("bg-success" if done else "bg-secondary")
            pills.append(ui.span(
                f"{mark} {t('start', key)}",
                class_=cls, title=status,
                style="font-size:0.95rem;padding:0.55em 0.9em;",
            ))
            if i < len(steps) - 1:
                pills.append(ui.span("›", class_="text-muted", style="font-size:1.2rem;"))
        return ui.div(*pills, class_="d-flex flex-wrap align-items-center gap-2")

    def _tile(btn_id, icon, title_key, body_key):
        return ui.input_action_button(
            btn_id,
            ui.div(
                ui.div(icon, class_="mb-2", style="font-size:1.6rem;"),
                ui.div(ui.tags.strong(t("start", title_key))),
                ui.div(t("start", body_key), class_="small text-muted"),
            ),
            class_="btn btn-outline-secondary w-100 h-100 text-start p-3",
        )

    def _config_line():
        # provider_select lives in the sidebar today; after phase 5 it is
        # gone and we fall back to the persisted current API.
        try:
            provider = input.provider_select()
        except Exception:
            provider = config.get_current_api()
        mdl = model.get()
        if not provider or not mdl:
            return ui.div(
                icon_svg("circle-info"), " ", t("start", "config_line_no_provider"),
                class_="alert alert-warning py-2 mb-0",
            )
        rv = api_keys.get(provider)
        has_key = bool(rv.get()) if rv is not None else False
        status = t("start", "config_line_ready") if has_key else t("start", "config_line_no_key")
        line = t("start", "config_line_template").format(
            provider=_PROVIDER_LABELS.get(provider, provider), model=mdl, status=status,
        )
        cls = "alert py-2 mb-0 " + ("alert-success" if has_key else "alert-warning")
        return ui.div(icon_svg("robot"), " ", line, class_=cls)

    def _dp_section():
        # Data-protection gate. None → must acknowledge before any LLM call;
        # "consent"/"fictive" → acknowledged with a recorded choice; ""
        # → acknowledged by a legacy flag file with no recorded choice.
        kind = state.data_consent_given.get()
        if kind is None:
            return ui.card(
                ui.card_header(ui.span(icon_svg("shield-halved"), " ",
                                       t("start", "dp_section_title"))),
                ui.p(ui.tags.strong(t("start", "dp_intro_strong"))),
                ui.p(t("start", "dp_intro_body")),
                ui.input_radio_buttons(
                    "start_dp_data_kind", None,
                    choices={
                        "consent": t("start", "dp_choice_consent"),
                        "fictive": t("start", "dp_choice_fictive"),
                    },
                    selected=None,
                ),
                ui.input_action_button(
                    "start_dp_confirm", t("start", "dp_confirm"),
                    icon=icon_svg("check"), class_="btn-success",
                ),
                ui.p(t("start", "dp_status_pending"),
                     class_="text-muted small mt-2 mb-0"),
                class_="border-warning",
            )
        kind_label = {"consent": t("start", "dp_kind_consent"),
                      "fictive": t("start", "dp_kind_fictive")}.get(kind)
        status = [icon_svg("circle-check"), " ", t("start", "dp_status_ok")]
        if kind_label:
            status.append(ui.tags.strong(" " + kind_label))
        return ui.div(
            ui.div(*status, class_="alert alert-success py-2 mb-1"),
            ui.input_action_button(
                "start_dp_change", t("start", "dp_change"),
                icon=icon_svg("pen"), class_="btn-outline-secondary btn-sm",
            ),
        )

    # ------------------------------------------------------------------
    # Main section
    # ------------------------------------------------------------------
    @render.ui
    def start_section():
        return ui.div(
            ui.h2(t("start", "intro_headline")),
            ui.p(t("start", "intro_body"), class_="text-muted"),
            _dp_section(),
            ui.card(
                ui.card_header(t("start", "workflow_title")),
                _workflow_strip(),
            ),
            ui.h5(t("start", "tiles_title"), class_="mt-3"),
            ui.layout_columns(
                _tile("start_tile_audio", icon_svg("microphone"),
                      "tile_audio_title", "tile_audio_body"),
                _tile("start_tile_transcript", icon_svg("file-arrow-up"),
                      "tile_transcript_title", "tile_transcript_body"),
                _tile("start_tile_resume", icon_svg("clock-rotate-left"),
                      "tile_resume_title", "tile_resume_body"),
                _tile("start_tile_demo", icon_svg("vial"),
                      "tile_demo_title", "tile_demo_body"),
                col_widths={"sm": 6, "lg": 3},
            ),
            ui.div(_config_line(), class_="mt-3"),
            # Quick-start checklist (moved out of the floating pill).
            ui.div(ui.output_ui("tt_quickstart_panel"), class_="mt-3"),
            ui.card(
                ui.card_header(t("start", "whats_new_title")),
                ui.tags.ul(
                    ui.tags.li(t("start", "whats_new_1")),
                    ui.tags.li(t("start", "whats_new_2")),
                    ui.tags.li(t("start", "whats_new_3")),
                    class_="mb-0",
                ),
                class_="mt-3",
            ),
            class_="p-2",
        )

    # ------------------------------------------------------------------
    # Tile actions — navigate / reuse existing code paths
    # ------------------------------------------------------------------
    @reactive.effect
    @reactive.event(input.start_tile_audio, ignore_init=True)
    def _go_transcription():
        ui.update_navset("main_tabs", selected=_NAV_TRANSCRIPTION)

    @reactive.effect
    @reactive.event(input.start_tile_transcript, ignore_init=True)
    def _go_analysis():
        ui.update_navset("main_tabs", selected=_NAV_ANALYSIS)

    @reactive.effect
    @reactive.event(input.start_tile_resume, ignore_init=True)
    def _open_history():
        fn = getattr(state, "show_history_modal", None)
        if fn is not None:
            fn()

    @reactive.effect
    @reactive.event(input.start_tile_demo, ignore_init=True)
    async def _load_demo():
        fn = getattr(state, "load_demo_session", None)
        if fn is not None:
            await fn()

    # ------------------------------------------------------------------
    # Data-protection acknowledgment
    # ------------------------------------------------------------------
    @reactive.effect
    @reactive.event(input.start_dp_confirm, ignore_init=True)
    def _confirm_dp():
        try:
            choice = input.start_dp_data_kind()
        except Exception:
            choice = None
        if choice not in ("consent", "fictive"):
            ui.notification_show(t("start", "dp_pick_required"), type="warning", duration=4)
            return
        _mark_dataprotection_acknowledged(choice)
        state.data_consent_given.set(choice)

    @reactive.effect
    @reactive.event(input.start_dp_change, ignore_init=True)
    def _change_dp():
        # Re-open the choice for this session. The on-disk flag is left intact;
        # re-confirming overwrites it. (Until re-confirmed, LLM calls are gated.)
        state.data_consent_given.set(None)
