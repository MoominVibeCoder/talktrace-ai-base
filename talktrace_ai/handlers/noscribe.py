"""noScribe local-transcription module: Analysis-tab section.

Drives the engine in ``utils.noscribe_engine`` (install / transcribe /
cancel / uninstall) through the same sync-generator → ``async_stream``
bridge the LLM streaming path uses. On a successful transcription the
result is handed off into ``transcript_data`` so the normal analysis flow
takes over.

UI is split into two reactive outputs to avoid input thrash:
- ``noscribe_section`` depends on ``noscribe_status`` only → renders the
  structural layout (install button / audio form / progress shell) once
  per state transition, so the file/select inputs aren't recreated on
  every progress tick.
- ``noscribe_progress_view`` depends on ``noscribe_progress`` only →
  re-renders rapidly during install/transcription (bar, phase, live log).
"""
from ._common import *

from ..utils import noscribe_engine


# Engine speaker labels start at S00; the handoff text is already
# renumbered to S01+ by the engine. We only need to drop noScribe's
# metadata header (everything before the first speaker line) so the
# preview and downstream parsers see a clean transcript.
_FIRST_SPEAKER_RE = re.compile(r"^S\d+:", re.MULTILINE)

# How many recent log lines to keep in the live view.
_LOG_KEEP = 8


def _strip_noscribe_header(text: str) -> str:
    if not text:
        return text
    m = _FIRST_SPEAKER_RE.search(text)
    return text[m.start():] if m else text


def _map_engine_state(engine_status) -> str:
    """EngineStatus.state → our reactive noscribe_status vocabulary."""
    if engine_status is None:
        return "not_installed"
    return {
        "ready": "ready",
        "not_installed": "not_installed",
        "broken": "broken",
    }.get(engine_status.state, "not_installed")


def register(state):
    input = state.input
    t = state.t
    config = state.config
    transcript_data = state.transcript_data

    noscribe_status = state.noscribe_status
    noscribe_progress = state.noscribe_progress
    noscribe_engine_status = state.noscribe_engine_status

    # ---- one-time detection (runs synchronously during server setup) ----
    initial = noscribe_engine.detect()
    noscribe_engine_status.set(initial)
    noscribe_status.set(_map_engine_state(initial))

    # Phase keys (from the engine events) → localized labels. Falls back to
    # the event's own English label if a key isn't mapped.
    def _phase_label(key: str, fallback: str) -> str:
        mapping = {
            # install phases
            "preflight": t("noscribe", "phase_preflight"),
            "uv": t("noscribe", "phase_uv"),
            "python": t("noscribe", "phase_python"),
            "noscribe": t("noscribe", "phase_noscribe"),
            "deps": t("noscribe", "phase_deps"),
            "model": t("noscribe", "phase_model"),
            "health": t("noscribe", "phase_health"),
            # transcription phases
            "setup": t("noscribe", "phase_setup"),
            "diarize": t("noscribe", "phase_diarize"),
            "whisper_load": t("noscribe", "phase_whisper_load"),
            "transcribe": t("noscribe", "phase_transcribe"),
            "save": t("noscribe", "phase_save"),
        }
        return mapping.get(key, fallback or key)

    # =====================================================================
    # Rendering
    # =====================================================================

    @render.ui
    def noscribe_section_title():
        return ui.span(
            icon_svg("microphone"), " ", t("noscribe", "section_title"),
        )

    @render.ui
    def noscribe_section():
        status = noscribe_status.get()
        if status in ("not_installed", "broken"):
            return _view_not_installed(status)
        if status == "installing":
            return _view_busy("installing")
        if status == "ready":
            return _view_ready()
        if status == "running":
            return _view_busy("running")
        if status == "error":
            return _view_error()
        return ui.p(t("noscribe", "checking"))

    def _view_not_installed(status):
        is_repair = status == "broken"
        children = [
            ui.p(t("noscribe", "not_installed_intro")),
            ui.tags.ul(
                ui.tags.li(t("noscribe", "bullet_local")),
                ui.tags.li(t("noscribe", "bullet_size")),
                ui.tags.li(t("noscribe", "bullet_gpl")),
            ),
        ]
        if not noscribe_engine._IS_WINDOWS:
            children.append(ui.div(
                t("noscribe", "windows_only"),
                class_="alert alert-warning", role="alert",
            ))
            return ui.div(*children)
        if is_repair:
            children.append(ui.div(
                t("noscribe", "broken_note"),
                class_="alert alert-warning", role="alert",
            ))
        children.append(ui.input_action_button(
            "noscribe_install",
            t("noscribe", "repair_button" if is_repair else "install_button"),
            icon=icon_svg("download"),
            class_="btn-success",
        ))
        return ui.div(*children)

    def _view_ready():
        engine_status = noscribe_engine_status.get()
        is_desktop = engine_status is not None and engine_status.mode == "desktop"

        # speaker count prefill: known group size beats "auto"
        try:
            n = int(input.num_pupils() or 0)
        except Exception:
            n = 0
        spk_choices = {"auto": t("noscribe", "speakers_auto")}
        for i in range(1, 11):
            spk_choices[str(i)] = str(i)
        spk_selected = str(n) if 1 <= n <= 10 else "auto"

        ui_lang = config.get_localization().get("current_language", "de")
        lang_choices = {
            "auto": t("noscribe", "language_auto"),
            "de": t("noscribe", "language_de"),
            "en": t("noscribe", "language_en"),
        }
        lang_selected = ui_lang if ui_lang in ("de", "en") else "auto"

        header = []
        if is_desktop:
            header.append(ui.div(
                icon_svg("circle-info"), " ", t("noscribe", "desktop_detected"),
                class_="alert alert-info", role="alert",
            ))

        return ui.div(
            *header,
            ui.p(t("noscribe", "ready_intro")),
            ui.layout_columns(
                ui.input_file(
                    "noscribe_audio",
                    t("noscribe", "audio_label"),
                    multiple=False,
                    accept=[".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".opus"],
                    button_label=t("analysis", "browse"),
                    placeholder=t("analysis", "placeholder"),
                ),
                ui.input_select(
                    "noscribe_language",
                    t("noscribe", "language_label"),
                    choices=lang_choices, selected=lang_selected,
                ),
                ui.input_select(
                    "noscribe_speakers",
                    t("noscribe", "speakers_label"),
                    choices=spk_choices, selected=spk_selected,
                ),
                col_widths=[6, 3, 3],
            ),
            ui.div(
                ui.input_action_button(
                    "noscribe_start",
                    t("noscribe", "start_button"),
                    icon=icon_svg("wand-magic-sparkles"),
                    class_="btn-success",
                ),
                ui.output_ui("noscribe_result_note"),
                style="display: flex; gap: 0.75rem; align-items: center;",
            ),
            ui.tags.hr(),
            ui.div(
                ui.tags.small(
                    t("noscribe", "engine_version").format(
                        version=(engine_status.info.get("noscribe_tag", "?")
                                 if engine_status and engine_status.info else "?")
                    ),
                    class_="text-muted",
                ),
                ui.input_action_link(
                    "noscribe_uninstall",
                    t("noscribe", "uninstall_button"),
                ) if not is_desktop else None,
                style="display: flex; gap: 1rem; align-items: center; justify-content: space-between;",
            ),
        )

    def _view_busy(kind):
        # kind: "installing" | "running"
        title_key = "installing_title" if kind == "installing" else "running_title"
        return ui.div(
            ui.h5(t("noscribe", title_key)),
            ui.output_ui("noscribe_progress_view"),
            ui.input_action_button(
                "noscribe_cancel_btn",
                t("noscribe", "cancel_button"),
                icon=icon_svg("circle-stop"),
                class_="btn-danger",
            ),
        )

    def _view_error():
        prog = noscribe_progress.get() or {}
        return ui.div(
            ui.div(
                ui.tags.strong(t("noscribe", "error_title")),
                ui.tags.br(),
                prog.get("error", ""),
                class_="alert alert-danger", role="alert",
            ),
            ui.tags.details(
                ui.tags.summary(t("noscribe", "error_log_summary")),
                ui.tags.pre(
                    "\n".join(prog.get("log_tail", [])),
                    style="max-height: 220px; overflow: auto; font-size: 0.8rem;",
                ),
            ) if prog.get("log_tail") else None,
            ui.input_action_button(
                "noscribe_install",
                t("noscribe", "error_retry"),
                icon=icon_svg("rotate-right"),
                class_="btn-warning",
            ),
        )

    @render.ui
    def noscribe_progress_view():
        prog = noscribe_progress.get()
        if not prog:
            return None
        phase_label = prog.get("phase_label") or ""
        value = prog.get("value")
        detail = prog.get("detail") or ""
        log = prog.get("log") or []

        bar_inner_style = (
            f"width: {max(0, min(100, value))}%;" if value is not None
            else "width: 100%;"
        )
        bar_classes = "progress-bar" + (
            " progress-bar-striped progress-bar-animated" if value is None else ""
        )
        parts = [
            ui.div(
                ui.tags.strong(phase_label),
                (ui.tags.span(f"  {detail}", class_="text-muted")
                 if detail else None),
                style="margin-bottom: 0.25rem;",
            ),
            ui.div(
                ui.div(
                    (f"{value}%" if value is not None else ""),
                    class_=bar_classes,
                    role="progressbar",
                    style=bar_inner_style,
                ),
                class_="progress",
                style="height: 1.25rem; margin-bottom: 0.5rem;",
            ),
        ]
        if log:
            parts.append(ui.tags.pre(
                "\n".join(log[-_LOG_KEEP:]),
                style=("max-height: 160px; overflow: auto; font-size: 0.8rem; "
                       "background: rgba(0,0,0,0.04); padding: 0.5rem; "
                       "border-radius: 4px; margin: 0;"),
            ))
        return ui.div(*parts, style="margin-bottom: 0.75rem;")

    @render.ui
    def noscribe_result_note():
        prog = noscribe_progress.get() or {}
        if prog.get("done"):
            return ui.span(
                icon_svg("check"), " ", t("noscribe", "done_msg"),
                style="color: #28a745;",
            )
        if prog.get("error"):
            return ui.span(
                icon_svg("triangle-exclamation"), " ", prog.get("error"),
                style="color: #d9534f;",
            )
        return None

    # =====================================================================
    # Progress-state helpers (called inside reactive.lock)
    # =====================================================================

    def _apply_event(ev):
        """Fold one engine event into the noscribe_progress dict."""
        cur = dict(noscribe_progress.get() or {})
        cur.pop("done", None)
        cur.pop("error", None)
        etype = ev.get("type")
        if etype == "phase":
            cur["phase"] = ev.get("key")
            cur["phase_label"] = _phase_label(ev.get("key"), ev.get("label"))
            cur["value"] = None
            cur["detail"] = ""
        elif etype == "progress":
            cur["value"] = ev.get("value")
            cur["detail"] = ev.get("detail", "")
        elif etype == "log":
            log = list(cur.get("log") or [])
            log.append(ev.get("line", ""))
            cur["log"] = log[-_LOG_KEEP * 3:]  # keep a little history for context
        noscribe_progress.set(cur)

    # =====================================================================
    # Install
    # =====================================================================

    async def _run_install():
        error = None
        cancelled = False
        log_tail = []
        try:
            async for ev in async_stream(
                noscribe_engine.install_engine,
                cancel_token=state.noscribe_cancel,
            ):
                etype = ev.get("type")
                if etype == "error":
                    error = ev.get("message")
                    log_tail = ev.get("log_tail", [])
                    break
                if etype == "cancelled":
                    cancelled = True
                    break
                if etype == "done":
                    continue
                async with reactive.lock():
                    _apply_event(ev)
                    await reactive.flush()
        except Exception as exc:  # pragma: no cover — defensive
            error = str(exc)
            print(f"[noscribe] install task failed: {exc!r}")

        async with reactive.lock():
            if cancelled:
                # Partial install dir may exist → re-detect, likely "broken".
                st = noscribe_engine.detect()
                noscribe_engine_status.set(st)
                noscribe_status.set(_map_engine_state(st))
                noscribe_progress.set(None)
            elif error:
                noscribe_status.set("error")
                noscribe_progress.set({"error": error, "log_tail": log_tail})
            else:
                st = noscribe_engine.detect()
                noscribe_engine_status.set(st)
                noscribe_status.set("ready")
                noscribe_progress.set(None)
            await reactive.flush()

    @reactive.effect
    @reactive.event(input.noscribe_install)
    def _kick_off_install():
        state.noscribe_cancel.reset()
        noscribe_progress.set({"phase_label": t("noscribe", "phase_preflight"),
                               "value": None})
        noscribe_status.set("installing")
        asyncio.create_task(_run_install())

    # =====================================================================
    # Transcription
    # =====================================================================

    async def _run_transcription(audio_path, language, speakers):
        result_text = None
        error = None
        cancelled = False
        log_tail = []
        try:
            async for ev in async_stream(
                noscribe_engine.run_transcription,
                audio_path,
                cancel_token=state.noscribe_cancel,
                language=language,
                speaker_detection=speakers,
            ):
                etype = ev.get("type")
                if etype == "done":
                    result_text = ev.get("text")
                    break
                if etype == "error":
                    error = ev.get("message")
                    log_tail = ev.get("log_tail", [])
                    break
                if etype == "cancelled":
                    cancelled = True
                    break
                async with reactive.lock():
                    _apply_event(ev)
                    await reactive.flush()
        except Exception as exc:  # pragma: no cover — defensive
            error = str(exc)
            print(f"[noscribe] transcription task failed: {exc!r}")

        async with reactive.lock():
            if cancelled:
                noscribe_status.set("ready")
                noscribe_progress.set(None)
            elif error:
                noscribe_status.set("ready")
                noscribe_progress.set({"error": error, "log_tail": log_tail})
            else:
                clean = _strip_noscribe_header(result_text or "")
                transcript_data.set(clean)
                try:
                    teacher = input.name_teacher() or None
                except Exception:
                    teacher = None
                valid = is_valid_transcript_format(clean, teacher)
                state.transcript_format_status.set("valid" if valid else "invalid")
                noscribe_status.set("ready")
                noscribe_progress.set({"done": True})
            await reactive.flush()

    @reactive.effect
    @reactive.event(input.noscribe_start)
    def _kick_off_transcription():
        file = None
        try:
            file = input.noscribe_audio()
        except Exception:
            file = None
        if not file:
            ui.modal_show(ui.modal(
                t("noscribe", "no_audio_selected"),
                title=t("noscribe", "section_title"),
                easy_close=True,
                footer=ui.modal_button(t("analysis", "modal_button_close"),
                                       class_="btn-success"),
            ))
            return
        audio_path = file[0]["datapath"]
        try:
            language = input.noscribe_language()
        except Exception:
            language = "auto"
        try:
            speakers = input.noscribe_speakers()
        except Exception:
            speakers = "auto"

        state.noscribe_cancel.reset()
        noscribe_progress.set({"phase_label": t("noscribe", "phase_setup"),
                               "value": None})
        noscribe_status.set("running")
        asyncio.create_task(_run_transcription(audio_path, language, speakers))

    @reactive.effect
    @reactive.event(input.noscribe_cancel_btn)
    def _cancel_noscribe():
        print("[noscribe] cancel requested by user")
        state.noscribe_cancel.cancel()

    # =====================================================================
    # Uninstall
    # =====================================================================

    @reactive.effect
    @reactive.event(input.noscribe_uninstall)
    def _ask_uninstall():
        ui.modal_show(ui.modal(
            t("noscribe", "uninstall_confirm"),
            title=t("noscribe", "uninstall_title"),
            easy_close=True,
            footer=ui.tags.div(
                ui.modal_button(t("analysis", "modal_button_cancel"),
                                class_="btn-secondary"),
                ui.input_action_button(
                    "noscribe_uninstall_confirm",
                    t("noscribe", "uninstall_button"),
                    class_="btn-danger",
                ),
            ),
        ))

    async def _run_uninstall():
        try:
            await asyncio.to_thread(noscribe_engine.uninstall_engine)
        except Exception as exc:
            print(f"[noscribe] uninstall failed: {exc!r}")
        async with reactive.lock():
            st = noscribe_engine.detect()
            noscribe_engine_status.set(st)
            noscribe_status.set(_map_engine_state(st))
            noscribe_progress.set(None)
            await reactive.flush()

    @reactive.effect
    @reactive.event(input.noscribe_uninstall_confirm)
    def _do_uninstall():
        ui.modal_remove()
        asyncio.create_task(_run_uninstall())
