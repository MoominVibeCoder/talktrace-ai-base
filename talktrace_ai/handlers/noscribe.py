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


# A turn line: "<speaker>: <text>" (S01:, Trinity:, …). Restrictive enough
# that prose with a mid-sentence colon doesn't get split into a new turn.
_TURN_LINE_RE = re.compile(r"^\s*([A-Za-z0-9ÄÖÜäöüß_./*\- ]{1,40}?):\s+(.*)$")


def _parse_turns_to_df(text: str, col_spk: str, col_txt: str):
    """Header-stripped transcript → one row per turn (speaker, utterance).
    Non-matching continuation lines fold into the previous turn's text."""
    import pandas as pd
    rows: list = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        m = _TURN_LINE_RE.match(line)
        if m:
            rows.append([m.group(1).strip(), m.group(2).strip()])
        elif rows:
            rows[-1][1] = (rows[-1][1] + " " + line.strip()).strip()
    return pd.DataFrame(rows, columns=[col_spk, col_txt])


def _df_to_transcript(df) -> str:
    """Turn rows → 'S0X: text' lines (the format the analysis consumes)."""
    if df is None:
        return ""
    lines = []
    for i in range(len(df)):
        spk = str(df.iat[i, 0]).strip()
        txt = str(df.iat[i, 1]).strip()
        if spk or txt:
            lines.append(f"{spk}: {txt}" if spk else txt)
    return "\n".join(lines)


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
    session = state.session
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

    # Turn-based editor state: one row per turn (speaker, utterance). Kept in
    # sync from transcript_data; cell edits update it; "Apply" reassembles it.
    turn_table_df = reactive.value(None)

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
        # Re-render on an explicit "Reset session" so the file input, the
        # start/stop fields and the waveform are cleared (this view otherwise
        # avoids casual re-renders on purpose — see _view_ready).
        state.session_reset_nonce.get()
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
            # --- waveform / trim (writes into the start/stop fields below) -
            ui.output_ui("noscribe_waveform"),
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
            # quality nudge: a fixed speaker count is the biggest free lever on
            # diarization quality, so reflect the current choice right here.
            ui.output_ui("noscribe_speakers_hint"),
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
        return ui.div(
            ui.tags.hr(),
            ui.h6(t("noscribe", "editor_title")),
            ui.p(t("noscribe", "editor_hint"),
                 class_="text-muted", style="font-size: 0.85rem;"),
            ui.output_data_frame("noscribe_turn_table"),
            ui.div(
                ui.input_action_button(
                    "noscribe_apply_edit", t("noscribe", "editor_apply"),
                    icon=icon_svg("check"), class_="btn-primary",
                ),
                # Save the (edited) transcript wherever the user wants — a
                # browser upload only gives us a temp copy of the audio, so we
                # can't write next to the original; a download lets the OS save
                # dialog pick the location (e.g. beside the audio file).
                ui.output_ui("noscribe_download_ui"),
                ui.tags.small(t("noscribe", "editor_apply_hint"),
                              class_="text-muted"),
                style=("display: flex; gap: 0.75rem; align-items: center; "
                       "margin-top: 0.5rem;"),
            ),
        )

    # Keep the turn table in sync with the current transcript. Fires when
    # transcript_data changes (new transcription, upload, or Apply) and on a
    # language switch (column labels). Cell edits update turn_table_df
    # directly (below) without touching transcript_data, so they survive.
    @reactive.effect
    def _sync_turn_table():
        txt = transcript_data.get()
        turn_table_df.set(_parse_turns_to_df(
            txt or "", t("noscribe", "editor_col_speaker"),
            t("noscribe", "editor_col_text")))

    @render.data_frame
    def noscribe_turn_table():
        df = turn_table_df.get()
        if df is None:
            df = _parse_turns_to_df(
                "", t("noscribe", "editor_col_speaker"),
                t("noscribe", "editor_col_text"))
        return render.DataGrid(
            df, editable=True, filters=False, width="100%", height="360px",
            styles=[{
                "cols": [0],
                "style": {"max-width": "110px", "font-family": "monospace",
                          "background-color": "var(--bs-primary-bg-subtle, #cfe2ff)"},
            }],
        )

    @noscribe_turn_table.set_patch_fn
    def _(*, patch):
        df = turn_table_df.get()
        if df is None:
            return patch["value"]
        df = df.copy()
        val = str(patch["value"]).strip()
        df.iat[patch["row_index"], patch["column_index"]] = val
        turn_table_df.set(df)
        return val

    @reactive.effect
    @reactive.event(input.noscribe_apply_edit)
    def _apply_transcript_edit():
        # reassemble the edited turn table into the S0X: transcript
        text = _df_to_transcript(turn_table_df.get())
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

    @render.ui
    def noscribe_speakers_hint():
        try:
            sel = input.noscribe_speakers()
        except Exception:
            sel = "auto"
        if sel == "auto":
            return ui.div(
                icon_svg("circle-info"), " ",
                t("noscribe", "speakers_hint_auto"),
                class_="alert alert-warning py-2 px-3 mb-3",
                role="alert", style="font-size: 0.9rem;",
            )
        if sel == "none":
            return None
        return ui.div(
            icon_svg("check"), " ",
            t("noscribe", "speakers_hint_fixed"),
            class_="text-success mb-3",
            style="font-size: 0.9rem;",
        )

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

    # --- waveform / trim widget -----------------------------------------
    # Serve the currently-selected audio file to the local webview so the
    # in-browser waveform widget can decode it; the widget writes the chosen
    # keep-range into noscribe_start_time / noscribe_stop_time (HH:MM:SS).
    # Audio stays on the machine — same arm's-length, local-only stance as the
    # transcription itself.
    _audio_ref = {"path": None, "mime": None}
    # Controllable mirror of "is an audio file selected?". Shiny does NOT clear a
    # file input's server-side value when its widget is re-rendered, so we can't
    # rely on input.noscribe_audio() going None on reset. Gate the waveform and
    # the transcription start on this flag instead, and clear it on reset.
    noscribe_has_audio = reactive.value(False)

    @reactive.effect
    @reactive.event(input.noscribe_audio)
    def _stash_audio_for_waveform():
        try:
            file = input.noscribe_audio()
        except Exception:
            file = None
        if file:
            import mimetypes
            name = file[0].get("name", "")
            _audio_ref["path"] = file[0].get("datapath")
            _audio_ref["mime"] = mimetypes.guess_type(name)[0] or "application/octet-stream"
            noscribe_has_audio.set(True)
        else:
            _audio_ref["path"] = None
            _audio_ref["mime"] = None
            noscribe_has_audio.set(False)

    @reactive.effect
    @reactive.event(lambda: state.session_reset_nonce.get(), ignore_init=True)
    def _clear_audio_on_reset():
        # "Reset session" must also drop the selected audio (the file input's
        # server value lingers, so clear our mirror) and the range/output fields.
        noscribe_has_audio.set(False)
        _audio_ref["path"] = None
        _audio_ref["mime"] = None
        ui.update_text("noscribe_start_time", value="")
        ui.update_text("noscribe_stop_time", value="")
        ui.update_text("noscribe_output_name", value="")

    def _serve_audio(request):
        from starlette.responses import FileResponse, Response
        path = _audio_ref.get("path")
        if not path or not os.path.exists(path):
            return Response(status_code=404)
        return FileResponse(path, media_type=_audio_ref.get("mime") or "application/octet-stream")

    _audio_route = session.dynamic_route("noscribe_audio_file", _serve_audio)

    @render.ui
    def noscribe_waveform():
        # Gate on our mirror so the waveform disappears on reset (the file
        # input's server value lingers and can't be relied on).
        if not noscribe_has_audio.get():
            return None
        try:
            file = input.noscribe_audio()
        except Exception:
            file = None
        if not file:
            return None
        # Cache-bust per UPLOAD (not per filename): each upload gets a unique
        # datapath, so re-uploading the SAME file still yields a fresh URL —
        # otherwise the rendered HTML would be byte-identical, Shiny would skip
        # the DOM update, and the widget would stay on the stale (already-inited)
        # state ("cutting blocked"). The dynamic route itself is stable.
        import hashlib
        dp = file[0].get("datapath", "") or file[0].get("name", "audio")
        bust = hashlib.md5(str(dp).encode("utf-8")).hexdigest()[:12]
        url = f"{_audio_route}?v={bust}"
        return ui.div(
            ui.tags.label(t("noscribe", "trim_label"), class_="form-label"),
            ui.tags.div(
                class_="ttai-trim",
                data_audio_url=url,
                data_start_input="noscribe_start_time",
                data_stop_input="noscribe_stop_time",
                data_label_play=t("noscribe", "trim_play"),
                data_label_pause=t("noscribe", "trim_pause"),
                data_label_reset=t("noscribe", "trim_reset"),
                data_label_region=t("noscribe", "trim_region"),
                data_label_decoding=t("noscribe", "trim_decoding"),
                data_label_failed=t("noscribe", "trim_failed"),
            ),
            ui.tags.small(t("noscribe", "trim_hint"), class_="text-muted"),
            style="margin-bottom:0.9rem;",
        )

    # ------------------------------------------------------------------
    # Save the transcript (.txt) — a download lets the OS save dialog pick
    # the location (a browser upload only gives us a temp copy of the audio,
    # so we can't write next to the original automatically).
    # ------------------------------------------------------------------
    def _txt_stem():
        with reactive.isolate():
            try:
                raw = (input.noscribe_output_name() or "").strip()
            except Exception:
                raw = ""
            try:
                audio = input.noscribe_audio()
            except Exception:
                audio = None
        stem = os.path.splitext(os.path.basename(raw))[0] if raw else ""
        if not stem and audio:
            stem = os.path.splitext(audio[0].get("name", "transcript"))[0]
        stem = re.sub(r"[^\w.\- ]+", "_", stem or "").strip()
        return stem or "transcript"

    @render.ui
    def noscribe_download_ui():
        # Re-renders on transcript changes: button appears once a transcript
        # exists and disappears on reset.
        if not (transcript_data.get() or "").strip():
            return None
        return ui.download_button(
            "noscribe_download_txt", t("noscribe", "download_txt"),
            icon=icon_svg("download"), class_="btn-primary btn-sm",
        )

    @render.download(filename=lambda: f"{_txt_stem()}.txt")
    def noscribe_download_txt():
        with reactive.isolate():
            txt = transcript_data.get() or ""
        yield txt.encode("utf-8")

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

    def _begin_install():
        state.noscribe_cancel.reset()
        noscribe_progress.set({"phase_label": t("noscribe", "phase_preflight"),
                               "value": None, "steps": list(_INSTALL_PHASES),
                               "t0": time.monotonic()})
        noscribe_status.set("installing")
        asyncio.create_task(_run_install())

    # Two separate effects rather than one @reactive.event(install, retry):
    # reactive.event's trigger evaluates *every* input on each fire, and the
    # retry button only exists in the error view. While it is absent,
    # input.noscribe_retry() raises SilentException, which aborts the whole
    # combined effect — so clicking Install/Repair (a different input) would
    # silently do nothing until the error view had been shown at least once.
    # Splitting them keeps each trigger independent of the other's presence.
    @reactive.effect
    @reactive.event(input.noscribe_install)
    def _kick_off_install():
        _begin_install()

    @reactive.effect
    @reactive.event(input.noscribe_retry)
    def _kick_off_retry():
        _begin_install()

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
        # `noscribe_has_audio` is our reset-aware mirror: a stale file-input
        # value must not let a transcription start after a reset.
        if not file or not noscribe_has_audio.get():
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
