"""Provider/model dropdowns + sync effects + provider hint."""
from .._common import *


def register(state):
    input = state.input
    config = state.config
    t = state.t
    current_api = state.current_api
    model = state.model

    def _provider_choices():
        # Built-ins + every registered custom provider (shared with the
        # Options-tab and Feedback dropdowns via provider_choices). LocalMind
        # (EU-hosted) leads as the GDPR-conformant default.
        # if state.local_only.get():
        #     return {"ollama": "Ollama"}
        return provider_choices(state)

    # Card header for the LLM-configuration card in the Analysis tab (the
    # model picker, switches, cost chip and analyse button now live there
    # instead of the sidebar).
    @render.ui
    def loc_llm_config_title():
        return ui.span(icon_svg("robot"), " ", t("analysis", "llm_config_title"))

    @render.ui
    def loc_dynamic_model_select():
        state.custom_providers.get()  # re-render when the registry changes
        return ui.div(
            ui.input_select("provider_select", t("sidebar", "provider_select"), choices=_provider_choices(), selected=config.get_current_api()),
            ui.input_select("model_select", t("sidebar", "model_select"), choices=state.select_api_choices(), selected=config.get_current_model()),
            **{"data-tt-help": t("onboarding", "tooltip_model_select")},
        )

    # Hinweis je nach Provider — als Tooltip auf einem kleinen Info-Icon,
    # damit die Sidebar nicht durch eine zusätzliche Textzeile aufgebläht
    # wird. Hover zeigt den Volltext.
    _PROVIDER_HINTS = {
        # Big-4 demo (May 2026): the original hints below corresponded to
        # providers that are commented out of KNOWN_PROVIDERS. Re-enable
        # together with their dropdown entries.
        # "ollama": ("ollama_cloud_hint_label", "ollama_cloud_hint"),
        # "groq": ("groq_quality_hint_label", "groq_quality_hint"),
        # "openrouter": ("openrouter_hint_label", "openrouter_hint"),
        "localmind": ("localmind_hint_label", "localmind_hint"),
        "mistral": ("mistral_hint_label", "mistral_hint"),
        "deepseek": ("deepseek_hint_label", "deepseek_hint"),
        "custom": ("custom_hint_label", "custom_hint"),
    }

    @render.ui
    def loc_provider_hint():
        try:
            provider = input.provider_select()
        except Exception:
            return None
        # Any custom:<id> provider shares the generic custom-endpoint hint.
        keys = _PROVIDER_HINTS.get(
            "custom" if is_custom_provider(provider) else provider)
        if not keys:
            return None
        label_key, text_key = keys
        return ui.tooltip(
            ui.tags.span(
                icon_svg("circle-info"),
                " ", t("sidebar", label_key),
                class_="text-muted small",
                style="cursor: help;",
            ),
            t("sidebar", text_key),
            placement="right",
        )

    @reactive.effect()
    def update_current_provider():
        selected_provider = input.provider_select()
        if not selected_provider:
            return
        if selected_provider == config.get_current_api():
            return
        config.set_current_api(selected_provider)
        current_api.set(selected_provider)
        # passendes erstes Modell des neuen Anbieters auswählen
        available_models = state.select_api_choices()
        if available_models:
            first_model = next(iter(available_models))
            model.set(first_model)
            config.set_current_model(first_model)
            ui.update_select("model_select", choices=available_models, selected=first_model)

    @reactive.effect()
    def update_current_model():
        # Beim (Re-)Mounten des Selects — z. B. Wechsel in den Analyse-Tab
        # über eine Start-Kachel — sendet der Browser transient null, ebenso
        # wenn das persistierte Modell nicht in den Choices steht. None darf
        # weder ins reactive model noch in configparser (TypeError: option
        # values must be strings) durchschlagen; der letzte gültige Wert
        # bleibt stehen.
        selected_model = input.model_select()
        if not selected_model:
            return
        model.set(selected_model)
        config.set_current_model(selected_model)
