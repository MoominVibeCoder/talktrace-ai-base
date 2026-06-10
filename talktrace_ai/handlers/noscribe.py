"""noScribe local-transcription module: dedicated Transcription tab.

Drives the engine in ``utils.noscribe_engine`` (install / download model /
transcribe / cancel / uninstall) through the same sync-generator →
``async_stream`` bridge the LLM streaming path uses. On a successful
transcription the result is handed off into ``transcript_data`` so the
normal analysis flow on the Analysis tab takes over.

The tab body is two reactive outputs to avoid input thrash:
- ``noscribe_section`` depends on ``noscribe_status`` only → renders the
  structural layout (install button / full options form / progress shell)
  once per state transition, so the file/select inputs aren't recreated on
  every progress tick.
- ``noscribe_progress_view`` depends on ``noscribe_progress`` only →
  re-renders rapidly during install/transcription (bar, phase, live log).

The options exposed mirror the noScribe GUI: audio in, output filename,
start/stop range, language, model (fast/precise, downloaded on demand),
speaker count, mark-pause, overlapping speech, disfluencies, timestamps.
"""
import time

from ._common import *

from ..utils import noscribe_engine


# Ordered phase keys per run type — drives the "step X of N" indicator.
_TRANSCRIBE_PHASES = ["setup", "diarize", "whisper_load", "transcribe", "save"]
_INSTALL_PHASES = ["preflight", "uv", "python", "noscribe", "deps", "model", "health"]


# Engine speaker labels start at S00; the handoff text is already
# renumbered to S01+ by the engine. We drop noScribe's metadata header
# (everything before the first speaker line) so the preview and downstream
# parsers see a clean transcript.
_FIRST_SPEAKER_RE = re.compile(r"^S\d+:", re.MULTILINE)

# Inline timestamp tokens noScribe writes when --timestamps is on. Stripped
# only for the analysis handoff (the saved/downloaded file keeps them).
_TS_TOKEN_RE = re.compile(r"\[?\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\]?")

_LOG_KEEP = 8


def _strip_noscribe_header(text: str) -> str:
    if not text:
        return text
    m = _FIRST_SPEAKER_RE.search(text)
    return text[m.start():] if m else text


def _noscribe_header(text: str) -> str:
    """The metadata block noScribe writes before the first speaker line
    (tool version, audio path, settings) — kept as provenance when we write
    edits back to the .txt."""
    if not text:
        return ""
    m = _FIRST_SPEAKER_RE.search(text)
    return text[:m.start()] if m else ""


def _strip_inline_timestamps(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        m = _FIRST_SPEAKER_RE.match(line)
        if m:
            label = line[:m.end()]
            body = _TS_TOKEN_RE.sub("", line[m.end():])
            out_lines.append((label + " " + body.strip()).rstrip())
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _map_engine_state(engine_status) -> str:
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

    # Last transcription's on-disk .txt + its noScribe metadata header, so
    # the editable transcript field can write corrections back to the file
    # (provenance) while preserving the header.
    last_output_path = reactive.value(None)
    last_header = reactive.value("")

    # ---- one-time detection (runs synchronously during server setup) ----
    initial = noscribe_engine.detect()
    noscribe_engine_status.set(initial)
    noscribe_status.set(_map_engine_state(initial))

    def _phase_label(key: str, fallback: str) -> str:
        mapping = {
            "preflight": t("noscribe", "phase_preflight"),
            "uv": t("noscribe", "phase_uv"),
            "python": t("noscribe", "phase_python"),
            "noscribe": t("noscribe", "phase_noscribe"),
            "deps": t("noscribe", "phase_deps"),
            "model": t("noscribe", "phase_model"),
            "health": t("noscribe", "phase_health"),
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

    @render.text
    def loc_title_transcription():
        return t("noscribe", "tab_title")

    @render.ui
    def noscribe_section_title():
        return ui.span(icon_svg("microphone"), " ", t("noscribe", "section_title"))

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

        # speaker count prefill: known group size beats "auto". Read inside
        # isolate() so an unrelated group-size change on the Analysis tab
        # doesn't re-render this whole section (which would wipe the editor
        # and the file input).
        try:
            with reactive.isolate():
                n = int(input.num_pupils() or 0)
        except Exception:
            n = 0
        spk_choices = {"none": t("noscribe", "speakers_none"),
                       "auto": t("noscribe", "speakers_auto")}
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

        # model dropdown: installed models plain, known-but-missing flagged.
        inst = set(noscribe_engine.installed_models(engine_status))
        model_choices = {}
        for name, spec in noscribe_engine.MODELS.items():
            if name in inst:
                model_choices[name] = name
            else:
                model_choices[name] = t("noscribe", "model_needs_download").format(
                    name=name, gb=spec["approx_gb"]
                )
        for name in sorted(inst):
            model_choices.setdefault(name, name)
        model_selected = (noscribe_engine.DEFAULT_MODEL
                          if noscribe_engine.DEFAULT_MODEL in model_choices
                          else next(iter(model_choices)))

        pause_choices = {
            "none": t("noscribe", "pause_none"),
            "1sec+": "1 sec+", "2sec+": "2 sec+", "3sec+": "3 sec+",
        }

        header = []
        if is_desktop:
            header.append(ui.div(
                icon_svg("circle-info"), " ", t("noscribe", "desktop_detected"),
                class_="alert alert-info", role="alert",
            ))

        return ui.div(
            *header,
            ui.p(t("noscribe", "ready_intro")),
            # --- file in / out -------------------------------------------
            ui.layout_columns(
                ui.input_file(
                    "noscribe_audio",
                    t("noscribe", "audio_label"),
                    multiple=False,
                    accept=[".wav", ".mp3", ".m4a", ".ogg", ".flac",
                            ".aac", ".wma", ".opus", ".mp4", ".mkv", ".mov"],
                    button_label=t("analysis", "browse"),
                    placeholder=t("analysis", "placeholder"),
                ),
                ui.input_text(
                    "noscribe_output_name",
                    t("noscribe", "output_label"),
                    value="", placeholder=t("noscribe", "output_placeholder"),
                ),
                col_widths=[6, 6],
            ),
            # --- core options --------------------------------------------
            ui.layout_columns(
                ui.input_select("noscribe_language", t("noscribe", "language_label"),
                                choices=lang_choices, selected=lang_selected),
                ui.input_select("noscribe_model", t("noscribe", "model_label"),
                                choices=model_choices, selected=model_selected),
                ui.input_select("noscribe_speakers", t("noscribe", "speakers_label"),
                                choices=spk_choices, selected=spk_selected),
                col_widths=[4, 4, 4],
            ),
            ui.layout_columns(
                ui.input_select("noscribe_pause", t("noscribe", "pause_label"),
                                choices=pause_choices, selected="none"),
                ui.input_text("noscribe_start_time", t("noscribe", "start_time_label"),
                              value="", placeholder="00:00:00"),
                ui.input_text("noscribe_stop_time", t("noscribe", "stop_time_label"),
                              value="", placeholder="00:00:00"),
                col_widths=[4, 4, 4],
            ),
            # --- toggles -------------------------------------------------
            ui.layout_columns(
                ui.input_checkbox("noscribe_overlapping",
                                  t("noscribe", "overlapping_label"), value=True),
                ui.input_checkbox("noscribe_disfluencies",
                                  t("noscribe", "disfluencies_label"), value=True),
                ui.input_checkbox("noscribe_timestamps",
                                  t("noscribe", "timestamps_label"), value=False),
                col_widths=[4, 4, 4],
            ),
            ui.div(
                ui.input_action_button(
                    "noscribe_start", t("noscribe", "start_button"),
                    icon=icon_svg("wand-magic-sparkles"), class_="btn-success",
                ),
                ui.output_ui("noscribe_result_note"),
                style="display: flex; gap: 0.75rem; align-items: center;",
            ),
            # --- editable transcript (human-in-the-loop) -----------------
            # Pre-filled from the current transcript (read via isolate so
            # typing here isn't wiped when transcript_data changes elsewhere).
            # After a transcription the section re-renders and this shows the
            # fresh result; "Apply" writes edits back into the shared
            # transcript_data that feeds the analysis.
            _transcript_editor(),
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
                    "noscribe_uninstall", t("noscribe", "uninstall_button"),
                ) if not is_desktop else None,
                style=("display: flex; gap: 1rem; align-items: center; "
                       "justify-content: space-between;"),
            ),
        )

    def _transcript_editor():
        with reactive.isolate():
            current = transcript_data.get() or ""
        return ui.div(
            ui.tags.hr(),
            ui.h6(t("noscribe", "editor_title")),
            ui.p(t("noscribe", "editor_hint"),
                 class_="text-muted", style="font-size: 0.85rem;"),
            ui.input_text_area(
                "noscribe_transcript_editor", None,
                value=current, width="100%", height="300px",
                placeholder=t("noscribe", "editor_placeholder"),
                spellcheck="true",
            ),
            ui.div(
                ui.input_action_button(
                    "noscribe_apply_edit", t("noscribe", "editor_apply"),
                    icon=icon_svg("check"), class_="btn-primary",
                ),
                ui.tags.small(t("noscribe", "editor_apply_hint"),
                              class_="text-muted"),
                style="display: flex; gap: 0.75rem; align-items: center;",
            ),
        )

    @reactive.effect
    @reactive.event(input.noscribe_apply_edit)
    def _apply_transcript_edit():
        try:
            text = input.noscribe_transcript_editor() or ""
        except Exception:
            text = ""
        # 1) feed the analysis (in-memory transcript)
        transcript_data.set(text)
        try:
            teacher = input.name_teacher() or None
        except Exception:
            teacher = None
        valid = is_valid_transcript_format(text, teacher)
        state.transcript_format_status.set("valid" if valid else "invalid")

        # 2) write corrections back to the on-disk .txt for provenance —
        # preserve noScribe's metadata header and stamp a manual-edit note.
        saved_to = None
        out = last_output_path.get()
        if out:
            try:
                header = (last_header.get() or "").rstrip()
                marker = t("noscribe", "editor_edit_marker").format(
                    date=date.today().isoformat())
                parts = [p for p in (header, marker, text.strip()) if p]
                Path(out).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
                saved_to = out
            except OSError as exc:
                print(f"[noscribe] could not write edited transcript: {exc!r}")

        if saved_to:
            ui.notification_show(
                t("noscribe", "editor_applied_saved").format(
                    file=os.path.basename(saved_to)),
                duration=5, type="message",
            )
        else:
            ui.notification_show(
                t("noscribe", "editor_applied"), duration=4, type="message",
            )

    def _view_busy(kind):
        title_key = "installing_title" if kind == "installing" else "running_title"
        return ui.div(
            # Own indeterminate-bar + spinner animation, NOT gated by
            # prefers-reduced-motion (Bootstrap disables its striped-bar and
            # slows its spinner under reduced-motion — which made the
            # indeterminate bar look like a finished, static full bar).
            # Defined once here (per run), used by noscribe_progress_view.
            ui.tags.style(
                "@keyframes ttai-indet {0%{left:-45%;}100%{left:100%;}}"
                "@keyframes ttai-spin {to{transform:rotate(360deg);}}"
                ".ttai-indet-track{position:relative;overflow:hidden;"
                "background:rgba(0,0,0,0.08);border-radius:0.25rem;}"
                ".ttai-indet-bar{position:absolute;top:0;bottom:0;width:45%;"
                "left:-45%;border-radius:0.25rem;"
                "background:var(--bs-primary,#0d6efd);"
                "animation:ttai-indet 1.1s infinite ease-in-out;}"
                ".ttai-spin{display:inline-block;width:1rem;height:1rem;"
                "border:0.16rem solid rgba(0,0,0,0.2);"
                "border-top-color:var(--bs-primary,#0d6efd);border-radius:50%;"
                "animation:ttai-spin 0.7s linear infinite;"
                "vertical-align:-0.15em;margin-right:0.45rem;}"
            ),
            ui.h5(t("noscribe", title_key)),
            ui.output_ui("noscribe_progress_view"),
            ui.input_action_button(
                "noscribe_cancel_btn", t("noscribe", "cancel_button"),
                icon=icon_svg("circle-stop"), class_="btn-danger",
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
                "noscribe_retry", t("noscribe", "error_retry"),
                icon=icon_svg("rotate-right"), class_="btn-warning",
            ),
        )

    @render.ui
    def noscribe_progress_view():
        prog = noscribe_progress.get()
        if not prog:
            return None
        phase_label = prog.get("phase_label") or ""
        phase_key = prog.get("phase")
        value = prog.get("value")
        detail = prog.get("detail") or ""
        log = prog.get("log") or []
        steps = prog.get("steps") or []
        t0 = prog.get("t0")

        # Tick the elapsed-time clock once a second while a run is live —
        # gives a visible "still working" signal during noScribe's long
        # silent compute phases (pyannote can churn for minutes with no
        # output line). invalidate_later re-runs this render on a timer.
        is_live = not prog.get("done") and not prog.get("error")
        if is_live and t0 is not None:
            reactive.invalidate_later(1.0)
            elapsed = max(0, int(time.monotonic() - t0))
            elapsed_txt = f"{elapsed // 60:d}:{elapsed % 60:02d}"
        else:
            elapsed_txt = None

        step_txt = ""
        if steps and phase_key in steps:
            step_txt = t("noscribe", "step_of").format(
                n=steps.index(phase_key) + 1, total=len(steps))

        header_bits = [
            ui.tags.span(
                ui.tags.span(class_="ttai-spin") if is_live else None,
                ui.tags.strong(phase_label),
            ),
        ]
        meta_bits = []
        if step_txt:
            meta_bits.append(ui.tags.span(step_txt, class_="text-muted"))
        if elapsed_txt is not None:
            meta_bits.append(ui.tags.span(
                icon_svg("clock"), " ", elapsed_txt, class_="text-muted"))

        # Determinate (known %) → filled bar with the number. Indeterminate
        # (value None, e.g. setup / model-load / pyannote compute) → our own
        # sliding bar so it visibly reads as "working", never a static full bar.
        if value is not None:
            bar = ui.div(
                ui.div(
                    f"{value}%",
                    class_="progress-bar", role="progressbar",
                    style=f"width: {max(0, min(100, value))}%;",
                ),
                class_="progress",
                style="height: 1.4rem; margin-bottom: 0.3rem;",
            )
        else:
            bar = ui.div(
                ui.div(class_="ttai-indet-bar"),
                class_="ttai-indet-track",
                style="height: 1.4rem; margin-bottom: 0.3rem;",
            )

        parts = [
            ui.div(
                ui.div(*header_bits),
                ui.div(*meta_bits, style="display: flex; gap: 1rem;"),
                style=("display: flex; justify-content: space-between; "
                       "align-items: baseline; margin-bottom: 0.3rem;"),
            ),
            bar,
        ]
        if detail:
            parts.append(ui.div(detail, class_="text-muted",
                                style="font-size: 0.8rem; margin-bottom: 0.5rem;"))
        if log:
            parts.append(ui.tags.details(
                ui.tags.summary(t("noscribe", "progress_log_summary"),
                                style="font-size: 0.8rem; cursor: pointer;"),
                ui.tags.pre(
                    "\n".join(log[-_LOG_KEEP:]),
                    style=("max-height: 160px; overflow: auto; font-size: 0.8rem; "
                           "background: rgba(0,0,0,0.04); padding: 0.5rem; "
                           "border-radius: 4px; margin: 0.3rem 0 0 0;"),
                ),
                open=True,
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

    # prefill the output filename from the chosen audio file's stem
    @reactive.effect
    @reactive.event(input.noscribe_audio)
    def _prefill_output_name():
        try:
            file = input.noscribe_audio()
        except Exception:
            file = None
        if file:
            stem = os.path.splitext(file[0].get("name", "transcript"))[0]
            ui.update_text("noscribe_output_name", value=stem)

    # =====================================================================
    # Progress-state helper (called inside reactive.lock)
    # =====================================================================

    def _apply_event(ev):
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
            cur["log"] = log[-_LOG_KEEP * 3:]
        noscribe_progress.set(cur)

    # =====================================================================
    # Install / repair
    # =====================================================================

    async def _run_install():
        error, cancelled, log_tail = None, False, []
        try:
            async for ev in async_stream(noscribe_engine.install_engine,
                                         cancel_token=state.noscribe_cancel):
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
        except Exception as exc:  # pragma: no cover
            error = str(exc)
            print(f"[noscribe] install task failed: {exc!r}")

        async with reactive.lock():
            if cancelled:
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
    @reactive.event(input.noscribe_install, input.noscribe_retry)
    def _kick_off_install():
        state.noscribe_cancel.reset()
        noscribe_progress.set({"phase_label": t("noscribe", "phase_preflight"),
                               "value": None, "steps": list(_INSTALL_PHASES),
                               "t0": time.monotonic()})
        noscribe_status.set("installing")
        asyncio.create_task(_run_install())

    # =====================================================================
    # Transcription (+ on-demand model download)
    # =====================================================================

    async def _run_transcription(audio_path, output_path, opts, need_model):
        result_text = None
        error, cancelled, log_tail = None, False, []
        ts_on = opts.get("timestamps", False)
        try:
            # 1) ensure the chosen model is present (downloads precise etc.)
            if need_model:
                async for ev in async_stream(noscribe_engine.download_model,
                                             opts["model"],
                                             cancel_token=state.noscribe_cancel):
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

            # 2) transcribe
            if not error and not cancelled:
                async for ev in async_stream(
                    noscribe_engine.run_transcription,
                    audio_path,
                    cancel_token=state.noscribe_cancel,
                    output_path=output_path,
                    language=opts["language"],
                    model=opts["model"],
                    speaker_detection=opts["speakers"],
                    overlapping=opts["overlapping"],
                    disfluencies=opts["disfluencies"],
                    timestamps=ts_on,
                    pause=opts["pause"],
                    start=opts["start"],
                    stop=opts["stop"],
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
        except Exception as exc:  # pragma: no cover
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
                if ts_on:
                    clean = _strip_inline_timestamps(clean)
                transcript_data.set(clean)
                # remember the .txt + its header so edits can be written back
                last_output_path.set(output_path)
                last_header.set(_noscribe_header(result_text or ""))
                try:
                    teacher = input.name_teacher() or None
                except Exception:
                    teacher = None
                valid = is_valid_transcript_format(clean, teacher)
                state.transcript_format_status.set("valid" if valid else "invalid")
                noscribe_status.set("ready")
                noscribe_progress.set({"done": True})
                # refresh installed-model list (precise may be new)
                noscribe_engine_status.set(noscribe_engine.detect())
            await reactive.flush()

    @reactive.effect
    @reactive.event(input.noscribe_start)
    def _kick_off_transcription():
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

        def _g(name, default=None):
            try:
                return input[name]()
            except Exception:
                return default

        model = _g("noscribe_model", noscribe_engine.DEFAULT_MODEL)
        opts = {
            "language": _g("noscribe_language", "auto"),
            "model": model,
            "speakers": _g("noscribe_speakers", "auto"),
            "pause": _g("noscribe_pause", "none"),
            "start": (_g("noscribe_start_time", "") or "").strip(),
            "stop": (_g("noscribe_stop_time", "") or "").strip(),
            "overlapping": bool(_g("noscribe_overlapping", True)),
            "disfluencies": bool(_g("noscribe_disfluencies", True)),
            "timestamps": bool(_g("noscribe_timestamps", False)),
        }

        # output filename → engine transcripts dir, always .txt (the format
        # the analysis consumes). User-entered name is sanitized to a stem.
        raw_name = (_g("noscribe_output_name", "") or "").strip()
        stem = os.path.splitext(os.path.basename(raw_name))[0] if raw_name else \
            os.path.splitext(file[0].get("name", "transcript"))[0]
        stem = re.sub(r'[^\w.\- ]+', "_", stem).strip() or "transcript"
        out_dir = noscribe_engine.engine_dir() / "transcripts"
        output_path = str(out_dir / f"{stem}.txt")

        need_model = not noscribe_engine.is_model_installed(
            model, noscribe_engine_status.get())

        state.noscribe_cancel.reset()
        steps = (["model"] if need_model else []) + list(_TRANSCRIBE_PHASES)
        first_phase = "phase_model" if need_model else "phase_setup"
        noscribe_progress.set({"phase_label": t("noscribe", first_phase),
                               "value": None, "steps": steps,
                               "t0": time.monotonic()})
        noscribe_status.set("running")
        asyncio.create_task(
            _run_transcription(audio_path, output_path, opts, need_model))

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
                ui.input_action_button("noscribe_uninstall_confirm",
                                       t("noscribe", "uninstall_button"),
                                       class_="btn-danger"),
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
