"""Feedback tab: LLM-generated formative feedback for the teacher.

Button-gated (NOT eager — it makes an LLM call). The provider/model pair is
picked in a tab-local selector (seeded from the global Analysis-tab choice,
overridable — feedback may use a cheaper model than the coding run), the key
comes from the OS keyring. Reads the analysis data already in AppState
(T-SEDA teacher-code profile + quantitative metrics), asks the model for
research-grounded formative feedback, shows it in an EDITABLE field, and
exports the (possibly edited) text as DOCX/PDF.

Pure prompt-assembly + DOCX rendering live in ``utils/feedback_section.py``;
the plain-text chat call lives in ``utils/llm_analysis/_freeform.py``. Feature
state is module-local (per the Consent convention), not on AppState.
"""
from ._common import *
from ..utils import feedback_section as fb
from ..utils.report_import import (
    ReportImportError,
    coded_turn_count,
    detect_teacher_label,
    parse_report,
    turns_to_transcript,
)
from ..utils.stats import count_pupils, dialog_stats


def register(state):
    input = state.input
    config = state.config
    t = state.t
    current_lang = state.current_lang

    # Module-local feature state (private to this tab — not on AppState).
    feedback_text = reactive.value(None)   # last generated prose; None until first run
    feedback_busy = reactive.value(False)  # True while the LLM call is in flight
    feedback_cost = reactive.value(None)   # per-call cost estimate in EUR
    imported_report = reactive.value(None)  # hand-checked coding table, or None

    def _S():
        return TRANSLATIONS[current_lang.get()]["feedback"]

    # ------------------------------------------------------------------
    # Localized titles
    # ------------------------------------------------------------------
    @render.text
    def loc_title_feedback():
        return t("feedback", "tab_title")

    @render.ui
    def feedback_section_title():
        return ui.span(icon_svg("comments"), " ", t("feedback", "section_title"))

    # ------------------------------------------------------------------
    # Helpers (read app state)
    # ------------------------------------------------------------------
    def _teacher_name():
        try:
            n = (input.name_teacher() or "").strip()
        except Exception:
            n = ""
        return n or t("analysis", "name_teacher_var")

    def _num_pupils():
        try:
            return int(input.num_pupils())
        except Exception:
            return state.num_participants.get() or 0

    def _key_for(provider):
        # Central resolver: built-in reactives + dynamic custom:<id> keys.
        return api_key_for(state, provider)

    def _has_analysis():
        return bool(state.analysis_state.get() and state.analysis_llm_state.get())

    def _has_data():
        """Genug Daten für ein Feedback — laufende Analyse ODER Report-Import."""
        return _has_analysis() or imported_report.get() is not None

    # ------------------------------------------------------------------
    # Report-Import
    # ------------------------------------------------------------------
    # Der übliche Weg im Feld: Report exportieren, die Codierungen in Word
    # oder Excel prüfen und korrigieren, dann hier wieder einlesen — das
    # Feedback soll auf der geprüften Fassung beruhen. Der Import trägt sich
    # selbst: Codes UND Kennzahlen kommen aus dem Dokument, damit er auch in
    # einer frischen Sitzung ohne vorherige Analyse funktioniert.
    def _report_source():
        """Datenquelle für das Feedback: (analysis_df, metrics) oder None.

        Ein importierter Report hat Vorrang vor der laufenden Analyse — er
        ist die bewusst hochgeladene, geprüfte Fassung.
        """
        frame = imported_report.get()
        if frame is None:
            return None
        # Lehrkraft-Label aus dem Report, nicht aus der App-Einstellung: heißt
        # sie dort "L", die App steht aber auf "LEHRER", fielen ihre Beiträge
        # still komplett aus den Kennzahlen (siehe detect_teacher_label).
        teacher = detect_teacher_label(frame, _teacher_name()) or _teacher_name()
        transcript = turns_to_transcript(frame, teacher)
        # Kennzahlen über denselben Weg wie im normalen Lauf: aus dem aus den
        # Turns zusammengesetzten Transkript. Kein zweiter Rechenpfad, der
        # gegenüber der Analyse auseinanderlaufen könnte.
        stats_df = dialog_stats(transcript, teacher)
        participants = count_pupils(transcript)
        pupils = _num_pupils()
        rate = (participants / pupils * 100) if pupils else 0.0
        metrics = fb.build_metrics(
            stats_df, num_participants=participants,
            participation_rate=rate, num_pupils=pupils, teacher_name=teacher,
        )
        return frame, metrics

    @reactive.effect
    @reactive.event(input.feedback_report_upload)
    def _process_report_upload():
        file = input.feedback_report_upload()
        if not file:
            return
        info = file[0]
        try:
            frame = parse_report(info["datapath"], info.get("name"))
        except ReportImportError as e:
            # Die Exception trägt einen Localization-Key als Nachricht.
            ui.notification_show(
                t("feedback", str(e)), type="error", duration=8,
            )
            imported_report.set(None)
            return
        imported_report.set(frame)
        feedback_text.set(None)   # altes Feedback passt nicht mehr zur Quelle
        feedback_cost.set(None)
        message = t("feedback", "import_ok").format(
            turns=len(frame), coded=coded_turn_count(frame),
        )
        # Weicht das Lehrkraft-Label im Report von der Einstellung ab, wird es
        # übernommen (sonst stimmen die Redeanteile nicht) — aber sichtbar,
        # nicht still: der Name steuert, was als Lehrkraft-Beitrag zählt.
        detected = detect_teacher_label(frame, _teacher_name())
        if detected and detected.strip().lower() != _teacher_name().strip().lower():
            message += " " + t("feedback", "import_teacher_label").format(
                label=detected,
            )
        ui.notification_show(message, type="message", duration=8)

    @reactive.effect
    @reactive.event(input.feedback_import_clear)
    def _clear_report_import():
        imported_report.set(None)
        feedback_text.set(None)
        feedback_cost.set(None)
        ui.notification_show(t("feedback", "import_cleared"),
                             type="message", duration=4)

    def _import_panel():
        """Upload-Block — immer sichtbar, auch ohne laufende Analyse."""
        frame = imported_report.get()
        parts = [
            ui.input_file(
                "feedback_report_upload", t("feedback", "upload_label"),
                accept=[".docx", ".xlsx", ".csv", ".zip", ".html", ".htm"],
                button_label=t("feedback", "upload_button"),
                placeholder=t("feedback", "upload_placeholder"),
                width="100%",
            ),
            ui.tags.p(t("feedback", "upload_hint"),
                      class_="text-muted small", style="margin-top:-0.5rem;"),
        ]
        if frame is not None:
            parts.append(ui.div(
                icon_svg("file-import"), " ",
                t("feedback", "import_active").format(
                    turns=len(frame), coded=coded_turn_count(frame),
                ),
                " ",
                ui.input_action_button(
                    "feedback_import_clear", t("feedback", "import_clear"),
                    class_="btn btn-sm btn-outline-secondary",
                    style="margin-left:0.5rem;",
                ),
                class_="alert alert-success py-2 px-3", role="alert",
                style="font-size:0.9rem;",
            ))
            # Ohne Codebuch kennt das Modell nur die Kürzel, nicht ihre
            # Bedeutung — im Report-Einstieg ist das der Normalfall.
            if not fb.extract_code_definitions(state.codebook_data.get()):
                parts.append(ui.div(
                    icon_svg("triangle-exclamation"), " ",
                    t("feedback", "import_no_codebook"),
                    class_="alert alert-warning py-2 px-3", role="alert",
                    style="font-size:0.9rem;",
                ))
        return ui.div(*parts, class_="mb-3")

    # ------------------------------------------------------------------
    # Main section
    # ------------------------------------------------------------------
    @render.ui
    def feedback_section():
        if not _has_data():
            # Kein Analyselauf — der Upload bleibt trotzdem da: einen
            # korrigierten Report einzuspielen ist ein vollwertiger Einstieg,
            # keine Ergänzung zu einer laufenden Sitzung.
            return ui.div(
                ui.div(icon_svg("circle-info"), " ",
                       t("feedback", "empty_state"),
                       class_="alert alert-info py-2 px-3", role="alert"),
                _import_panel(),
            )

        busy = feedback_busy.get()
        txt = feedback_text.get()
        gen_label = (
            t("feedback", "generating") if busy
            else (t("feedback", "regenerate_button") if txt
                  else t("feedback", "generate_button"))
        )

        controls = ui.div(
            ui.input_action_button(
                "feedback_generate", gen_label,
                icon=icon_svg("wand-magic-sparkles"), class_="btn-primary",
                disabled=busy,
            ),
            # Downloads stay disabled until there is feedback to export
            # (and while a call is in flight) — otherwise they'd hand back an
            # empty document.
            ui.download_button(
                "feedback_download_docx", t("feedback", "download_docx"),
                icon=icon_svg("file-word"), class_="btn-success",
                disabled=busy or not txt,
            ),
            ui.download_button(
                "feedback_download_pdf", t("feedback", "download_pdf"),
                icon=icon_svg("file-pdf"), class_="btn-danger",
                disabled=busy or not txt,
            ),
            style="display:flex; gap:0.6rem; margin-bottom:0.75rem; flex-wrap:wrap;",
        )

        disclaimer = ui.div(
            icon_svg("circle-info"), " ", t("feedback", "disclaimer"),
            class_="alert alert-warning py-2 px-3", role="alert",
            style="font-size:0.9rem;",
        )

        parts = [ui.p(t("feedback", "intro_hint")), disclaimer,
                 _import_panel(), _llm_selector(), controls]

        if busy:
            parts.append(ui.div(
                ui.tags.span(class_="spinner-border spinner-border-sm", role="status"),
                " ", t("feedback", "generating"),
                class_="text-muted", style="padding:0.5rem 0;",
            ))

        if txt:
            # Seed the editable field from the live edited value (read under
            # isolate so keystrokes don't re-render); fall back to the generated
            # text. A successful (re)generation pushes the fresh text via
            # update_text_area below, so regenerate shows the new feedback while
            # an incidental re-render (e.g. language switch) preserves edits.
            with reactive.isolate():
                try:
                    edited = input.feedback_text_edit()
                except Exception:
                    edited = None
            seed = edited if edited else txt
            cost = feedback_cost.get()
            cost_chip = (
                ui.tags.small(
                    t("feedback", "cost_estimate").format(cost=_fmt_cost(cost)),
                    class_="text-muted",
                ) if cost else None
            )
            parts.append(ui.div(
                ui.p(t("feedback", "editor_hint"),
                     class_="text-muted", style="font-size:0.85rem;"),
                ui.input_text_area(
                    "feedback_text_edit", t("feedback", "editor_label"),
                    value=seed, rows=20, width="100%",
                ),
                ui.tags.button(
                    icon_svg("copy"), " ", t("feedback", "copy"),
                    type="button", class_="btn btn-sm btn-outline-secondary",
                    style="margin-top:0.4rem;",
                    onclick=("navigator.clipboard.writeText("
                             "document.getElementById('feedback_text_edit').value)"),
                ),
                cost_chip,
            ))
        elif not busy:
            parts.append(ui.div(
                ui.p(t("feedback", "preview_empty"),
                     style="color:#888; text-align:center; padding:2rem 1rem;"),
            ))

        return ui.div(*parts)

    def _fmt_cost(cost):
        s = f"{cost:.2f}"
        return s.replace(".", ",") if current_lang.get() == "de" else s

    # ------------------------------------------------------------------
    # LLM selection (local to this tab)
    # ------------------------------------------------------------------
    # The feedback call previously reused the global Analysis-tab choice
    # silently; now the provider/model pair is visible and overridable here —
    # feedback with a cheaper (or different) model than the coding run is a
    # legitimate combination. Starts synced to the global choice; the local
    # pick lives only in these inputs (per the module-local state convention).
    def _provider_choices():
        # Same provider set as sidebar/_model_select and options — built-ins
        # plus every registered custom provider (by name).
        return provider_choices(state)

    def _llm_selector():
        # Read the current picks under isolate: this section re-renders on
        # every busy/text change, and a plain read would both add an unwanted
        # reactive dependency and reset the dropdowns to the global default.
        with reactive.isolate():
            try:
                sel_provider = input.feedback_provider()
            except Exception:
                sel_provider = None
            try:
                sel_model = input.feedback_model()
            except Exception:
                sel_model = None
        provider = sel_provider or config.get_current_api()
        models = config.get_models(provider=provider)
        model = sel_model if sel_model in models else (
            state.model.get() if state.model.get() in models
            else (models[0] if models else None))
        return ui.div(
            ui.layout_columns(
                ui.input_select("feedback_provider",
                                t("sidebar", "provider_select"),
                                choices=_provider_choices(), selected=provider),
                ui.input_select("feedback_model",
                                t("sidebar", "model_select"),
                                choices=models, selected=model),
                col_widths=[4, 4],
            ),
            ui.tags.p(t("feedback", "llm_hint"),
                      class_="text-muted small", style="margin-top:-0.5rem;"),
        )

    @reactive.effect
    @reactive.event(input.feedback_provider, ignore_init=True)
    def _sync_feedback_models():
        # Provider switched — repopulate the model dropdown from the registry.
        models = config.get_models(provider=input.feedback_provider())
        with reactive.isolate():
            try:
                current = input.feedback_model()
            except Exception:
                current = None
        selected = current if current in models else (models[0] if models else None)
        ui.update_select("feedback_model", choices=models, selected=selected)

    # ------------------------------------------------------------------
    # Generate (button-gated LLM call)
    # ------------------------------------------------------------------
    @reactive.effect
    @reactive.event(input.feedback_generate)
    async def _generate():
        if feedback_busy.get() or not _has_data():
            return
        # Data-protection gate (Feedback always calls the LLM). Guide the user
        # to the Start tab where the acknowledgment widget lives.
        if state.data_consent_given.get() is None:
            ui.update_navset("main_tabs", selected='<div id="loc_title_start" class="shiny-text-output"></div>')
            ui.notification_show(t("start", "dp_status_pending"), type="warning", duration=6)
            return
        # Use the tab-local LLM pick (falls back to the global choice while
        # the selector has not rendered yet, e.g. programmatic generation).
        try:
            provider = input.feedback_provider() or config.get_current_api()
        except Exception:
            provider = config.get_current_api()
        try:
            model = input.feedback_model() or state.model.get()
        except Exception:
            model = state.model.get()
        key = _key_for(provider)
        if not key:
            ui.notification_show(t("feedback", "no_key"), type="warning", duration=6)
            return

        teacher = _teacher_name()
        code_defs = fb.extract_code_definitions(state.codebook_data.get())
        # Ein importierter Report gewinnt gegen die laufende Analyse: er ist
        # die bewusst hochgeladene, von Hand geprüfte Fassung.
        source = _report_source()
        if source is not None:
            analysis_df, metrics = source
        else:
            data = state.llm_analysis_data.get()
            analysis_df = data[-1] if data else None
            metrics = fb.build_metrics(
                state.stats.get(),
                num_participants=state.num_participants.get(),
                participation_rate=state.participation_rate.get(),
                num_pupils=_num_pupils(),
                teacher_name=teacher,
            )
        profile = fb.teacher_code_profile(analysis_df, teacher)
        lang = current_lang.get()
        sys_p, usr_p = fb.build_feedback_prompts(
            lang=lang, model=model, metrics=metrics,
            code_definitions=code_defs, code_profile=profile,
        )

        feedback_busy.set(True)
        try:
            result = await asyncio.to_thread(
                lambda: chat_completion(
                    provider, model, sys_p, usr_p, key,
                    base_url=(config.custom_base_url(provider)
                              if is_custom_provider(provider) else None),
                ),
            )
            result = fb.clean_markdown(result)  # plain text — no md in the field
            feedback_text.set(result)
            # Push the fresh text into the (mounted) editable field so a
            # regeneration replaces any prior edits with the new feedback.
            ui.update_text_area("feedback_text_edit", value=result)
            _log_cost(provider, model, sys_p, usr_p, result)
        except RuntimeError as exc:
            marker = str(exc).split(":", 1)[0].strip()
            if marker == "feedback_empty":
                msg = t("feedback", "feedback_empty")
            else:
                msg = t("feedback", "feedback_failed").format(error=str(exc))
            ui.notification_show(msg, type="error", duration=8)
        except Exception as exc:  # noqa: BLE001
            ui.notification_show(
                t("feedback", "feedback_failed").format(error=str(exc)),
                type="error", duration=8,
            )
        finally:
            feedback_busy.set(False)

    def _log_cost(provider, model, sys_p, usr_p, result):
        """Estimate this feedback call's cost (tiktoken + registry pricing) and
        append it to the shared cost log, tagged group_id='feedback'. Best-effort
        — a missing price entry or encoding just skips logging."""
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            in_tok = len(enc.encode(f"{sys_p}\n{usr_p}"))
            out_tok = len(enc.encode(result or ""))
            rate = config.get_api_pricing().get(provider, {}).get(model)
            if not rate:
                return
            cost = (in_tok / 1_000_000) * rate["input"] + (out_tok / 1_000_000) * rate["output"]
            feedback_cost.set(cost)
            record_cost_run(provider, model, cost, input_tokens=in_tok, group_id="feedback")
            state.cost_tracker_version.set(state.cost_tracker_version.get() + 1)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Download: editable Word (.docx) and PDF (Word → PDF via docx2pdf)
    # ------------------------------------------------------------------
    def _stem():
        with reactive.isolate():
            try:
                g = (input.name_group() or "").strip()
            except Exception:
                g = ""
        if g:
            safe = re.sub(r"[^\w\-]+", "_", g).strip("_")
            if safe:
                return f"Feedback_{safe}"
        return "Feedback"

    def _current_text():
        """The text to export: the (possibly edited) field, else the generated."""
        with reactive.isolate():
            try:
                edited = input.feedback_text_edit()
            except Exception:
                edited = None
            generated = feedback_text.get()
        return (edited if edited else generated) or ""

    def _write_docx(target_path):
        with reactive.isolate():
            lang = current_lang.get()
            S = _S()
        fb.write_feedback_docx(
            target_path, _current_text(), lang=lang,
            doc_title=S["doc_title"], disclaimer=S["disclaimer"],
        )

    @render.download(filename=lambda: f"{_stem()}.docx")
    def feedback_download_docx():
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = tmp.name
        _write_docx(tmp_path)
        with open(tmp_path, "rb") as fh:
            yield fh.read()
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    @render.download(filename=lambda: f"{_stem()}.pdf")
    def feedback_download_pdf():
        # PDF needs Word (COM on Windows / AppleScript on macOS); unavailable on
        # Linux — surface a clean localized message instead of a COM traceback.
        if sys.platform.startswith("linux"):
            ui.notification_show(
                t("feedback", "pdf_unavailable_linux"), type="error", duration=8,
            )
            return
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            docx_path = tmp.name
        pdf_path = docx_path[:-5] + ".pdf"
        try:
            _write_docx(docx_path)
            from docx2pdf import convert as _docx2pdf_convert
            _docx2pdf_convert(docx_path, pdf_path)
            with open(pdf_path, "rb") as fh:
                yield fh.read()
        except Exception as exc:  # noqa: BLE001
            ui.notification_show(
                t("feedback", "pdf_failed").format(error=str(exc)),
                type="error", duration=8,
            )
            return
        finally:
            for p in (docx_path, pdf_path):
                try:
                    os.remove(p)
                except OSError:
                    pass
