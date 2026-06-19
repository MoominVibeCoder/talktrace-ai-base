"""Results section: quantitative + qualitative output panels."""
from ._common import *

from ..utils.codebook_hierarchy import build_priority_lookup, priority_for
from ..utils.plot_style import (
    apply_axes_style,
    primary_color,
    resolve_mode,
    round_bar_corners,
    secondary_color,
    stack_colors,
    style_no_data_axes,
)


def _no_data_fig(message, mode):
    """Blank placeholder figure with a centered message.

    Returns ``(fig, ax)`` so callers can pick what to return — render.plot
    handlers return ``fig``, reactive.calc internals often return ``ax``.
    """
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12)
    ax.axis('off')
    style_no_data_axes(ax, mode)
    return fig, ax


def _is_multi_coding_on(input_obj) -> bool:
    """Read the sidebar switch defensively. The switch is only rendered when
    LLM analysis is active, so before that input.multi_coding_switch() raises.
    Default: False (single-coding, hierarchy-resolved)."""
    try:
        return bool(input_obj.multi_coding_switch())
    except Exception:
        return False


def register(state):
    input = state.input
    output = state.output
    session = state.session
    t = state.t
    transcript_data = state.transcript_data
    codebook_data = state.codebook_data
    converted_transcript = state.converted_transcript
    num_participants = state.num_participants
    participation_rate = state.participation_rate
    stats = state.stats
    stats_per_speaker = state.stats_per_speaker
    llm_analysis_data = state.llm_analysis_data
    analysis_state = state.analysis_state
    analysis_llm_state = state.analysis_llm_state
    sim_plot = state.sim_plot
    qual_plot = state.qual_plot
    qual_stats_df = state.qual_stats_df
    code_edits = state.code_edits
    placeholder_plot = state.placeholder_plot
    code_legend_storage = state.code_legend_storage

    ### Ergebnisse --------------------------------------------------------
    # Ergebnisse Tab Titel
    @render.ui
    def loc_title_results():
        return tab_title_with_badge(
            t("results", "tab_title"),
            state.tab_badge_results.get(),
        )


    # Tab-Badge: bei Besuch des Results-Tabs den "unread"-Punkt auf "read"
    # umflaggen. Bleibt sichtbar (grün), damit man weiterhin sieht, dass
    # dort Daten liegen.
    @reactive.effect
    @reactive.event(input.main_tabs)
    def _flip_results_badge_on_visit():
        if main_tab_is(input.main_tabs(), "loc_title_results"):
            if state.tab_badge_results.get() == "unread":
                state.tab_badge_results.set("read")

    # Warnung, wenn Ergebnisse Tab ohne Analyse angeklickt wird
    @reactive.effect
    @reactive.event(input.main_tabs)
    def warn_if_results_tab_clicked():
        if not main_tab_is(input.main_tabs(), "loc_title_results"):
            return
        if analysis_state.get():
            return

        # Notification rather than a modal: a modal_show together with the
        # immediate update_navset below could leave the Bootstrap backdrop
        # stuck behind the next tab if the user clicked on. The demo entry
        # now lives on the Start tab, so no in-modal demo button is needed.
        ui.notification_show(
            t("onboarding", "empty_results_message"),
            type="message",
            duration=6,
        )
        ui.update_navset("main_tabs", selected='<div id="loc_title_analysis" class="shiny-text-output"></div>')

    # Anzeige der allgemeinen Informationen
    @render.ui
    def loc_quantitative_analysis():
        return ui.span(t("results", "section_quantitative_analysis"))


    # Die Berechnung der Stats-Werte (t_turns, p_turns, ...) erfolgt jetzt
    # direkt in run_analysis(), damit sie auch ohne gerenderten Results-Tab
    # für Report-Download und Session-Export verfügbar sind.


    # Anzeige der Gruppen-ID
    @render.ui
    def loc_group_id_display():
        return ui.value_box(
                        ui.p(t("analysis", "group_id")),
                        ui.output_text("nameGroup"),
                        showcase=icon_svg("id-card"),
                    ),


    @render.text
    def nameGroup():
        return input.name_group()


    # Anzeige der Klassengröße
    @render.ui
    def loc_class_size():
        return ui.value_box(
                        ui.p(t("results", "class_size")),
                        ui.output_text("numPupils"),
                        showcase=icon_svg("user-group"),
                    ),


    @render.text
    def numPupils():
        return input.num_pupils()


    # Anzeige der Anzahl beteiligter Schüler:innen
    @render.ui
    def loc_num_participants():
        return ui.value_box(
                        ui.p(t("results", "num_participants")),
                        ui.output_text("numParticipants"),
                        showcase=icon_svg("user-check"),
                    ),


    @render.text
    def numParticipants():
        req(num_participants.get() != None)
        return num_participants.get()


    # Anzeige der Beteiligungsquote
    @render.ui
    def loc_participation_rate():
        return ui.value_box(
                        ui.p(t("results", "participation_rate")),
                        ui.output_text("participationRate"),
                        showcase=icon_svg("square-poll-vertical"),
                    ),


    @render.text
    def participationRate():
        req(participation_rate.get() is not None)
        return f"{round(participation_rate.get(), 2)} %"


    # Verteilung der Gesprächsbeiträge
    @render.ui
    def loc_distribution_of_turns():
        return ui.p(t("results", "distribution_of_turns"))


     # Create a bar plot for quantitative statistics
    @reactive.calc
    def make_sim_stats_plot():
        req(transcript_data.get() != None)

        mode = resolve_mode(input)
        stats_df = stats.get()
        distribution = stats_df.plot(
            kind='bar', x='Sprecher', y='Gesamt_Woerter',
            alpha=1, rot=0, width=0.55, color=primary_color(mode),
        )
        distribution.set_xlabel(t("results", "words_total"))
        distribution.set_ylabel(t("results", "quantity"))
        legend = distribution.get_legend()
        if legend is not None:
            legend.remove()
        total = stats_df['Gesamt_Woerter'].sum() or 1  # avoid div-by-zero when empty
        # Build tick labels matching whatever rows are actually present in stats_df.
        # Map each speaker row to teacher or students using the user-provided name.
        teacher_label = t("stats", "teacher")
        students_label = t("stats", "students")
        teacher_name = input.name_teacher() or t("analysis", "name_teacher_var")
        tick_labels = [
            teacher_label if str(spk) == teacher_name else students_label
            for spk in stats_df['Sprecher'].tolist()
        ]
        distribution.set_xticks(range(len(tick_labels)))
        distribution.set_xticklabels(tick_labels)
        for container in distribution.containers:
            perc_labels = [f"{(bar.get_height() / total * 100):.1f}%" for bar in container]

            distribution.bar_label(container, label_type='center')
            distribution.bar_label(container, labels=perc_labels, label_type='edge')

        round_bar_corners(distribution)
        apply_axes_style(distribution, mode)
        sim_plot.set(distribution)
        return distribution


    # Plot für Gesprächsverteilung
    @render.plot(alt="placeholder", height=260)
    def sim_stats_plot():
        if analysis_state.get() == False:
            fig, _ = _no_data_fig(t("results", "no_data"), resolve_mode(input))
            return fig
        else:
            return make_sim_stats_plot()


    @render.ui
    def loc_over_time_quant_title():
        return ui.span(t("results", "over_time_quant_title"))


    def _segment_labels_for(n_segments):
        if n_segments == 3:
            return [t("results", "section_first"),
                    t("results", "section_middle"),
                    t("results", "section_last")]
        return [f"{t('results', 'section')} {i + 1}" for i in range(n_segments)]

    state.segment_labels_for = _segment_labels_for


    @reactive.calc
    def make_sim_stats_over_time_plot():
        req(transcript_data.get() is not None)
        mode = resolve_mode(input)
        transcript = transcript_data.get()
        teacher = input.name_teacher() or t("analysis", "name_teacher_var")
        n_segments = 3
        df = dialog_stats_over_time(
            transcript, teacher,
            n_segments=n_segments,
            segment_labels=_segment_labels_for(n_segments),
        )
        if df.empty:
            _, ax = _no_data_fig(t("results", "no_data"), mode)
            return ax
        pivot = df.pivot(index="Abschnitt", columns="Sprecher_Gruppe", values="Wörter") \
                  .reindex(_segment_labels_for(n_segments))
        ax = pivot.plot(
            kind='bar', rot=0, alpha=1, width=0.7,
            color=[primary_color(mode), secondary_color(mode)],
        )
        ax.set_xlabel(t("results", "section"))
        ax.set_ylabel(t("results", "words_total"))
        ax.legend(loc="upper right", fontsize=8, title=None)
        for container in ax.containers:
            ax.bar_label(container, label_type='edge', fontsize=8)
        round_bar_corners(ax)
        apply_axes_style(ax, mode)
        return ax

    state.make_sim_stats_over_time_plot = make_sim_stats_over_time_plot


    @render.plot(alt="placeholder", height=240)
    def sim_stats_over_time_plot():
        if not analysis_state.get():
            fig, _ = _no_data_fig(t("results", "no_data"), resolve_mode(input))
            return fig
        return make_sim_stats_over_time_plot()

    # Gesprächsstatistiken
    @render.ui
    def loc_interaction_turns():
        return ui.p(t("results", "interaction_turns"))

    # Lehrperson
    @render.ui
    def loc_teacher():
        return ui.p(t("results", "teacher"))


    # Display the TOTAL number of turns (teacher + all students).
    @render.text
    def teacher_impulses():
        req(stats.get() is not None and not stats.get().empty)
        total_turns = int(stats.get()['Anzahl_Beitraege'].sum())
        return total_turns


    # Schüler:innen
    @render.ui
    def loc_pupils():
        return ui.p(t("results", "students"))


    # ---- Neue Boxen: Beiträge mit Ø-Länge, längster Lehrer-Beitrag,
    #      Anteil Kurzantworten ------------------------------------------

    def _box_value(main: str, subtitle: str | None = None):
        if subtitle:
            return ui.tags.span(
                ui.tags.span(main),
                ui.tags.span(subtitle, class_="vb-subvalue"),
            )
        return ui.tags.span(main)


    @render.ui
    def loc_teacher_turns_box():
        return ui.markdown(f"**{t('results', 'teacher_turns_box')}**")


    @render.ui
    def teacher_turns_with_avg():
        req(analysis_state.get(), transcript_data.get() is not None)
        df = stats.get()
        teacher = input.name_teacher()
        count_row = df.loc[df['Sprecher'] == teacher, 'Anzahl_Beitraege']
        avg_row = df.loc[df['Sprecher'] == teacher, 'Durchschnitt_Woerter']
        count = int(count_row.values[0]) if not count_row.empty else 0
        avg = round(float(avg_row.values[0]), 1) if not avg_row.empty else 0
        return _box_value(str(count), t("results", "avg_words_subtitle").format(n=avg))


    @render.ui
    def loc_longest_teacher_turn():
        return ui.markdown(f"**{t('results', 'longest_teacher_turn')}**")


    @render.ui
    def longest_teacher_turn():
        req(analysis_state.get(), transcript_data.get() is not None)
        teacher = input.name_teacher() or t("analysis", "name_teacher_var")
        turns = _parse_turns(transcript_data.get(), teacher)
        teacher_lengths = [len(utt.split()) for spk, utt in turns if spk == teacher]
        max_len = max(teacher_lengths) if teacher_lengths else 0
        return _box_value(str(max_len), t("results", "words_unit"))


    @render.ui
    def loc_pupils_turns_box():
        return ui.markdown(f"**{t('results', 'pupils_turns_box')}**")


    @render.ui
    def pupils_turns_with_avg():
        req(analysis_state.get(), transcript_data.get() is not None)
        df = stats.get()
        count_row = df.loc[df['Sprecher'] == "Schüler:innen", 'Anzahl_Beitraege']
        avg_row = df.loc[df['Sprecher'] == "Schüler:innen", 'Durchschnitt_Woerter']
        count = int(count_row.values[0]) if not count_row.empty else 0
        avg = round(float(avg_row.values[0]), 1) if not avg_row.empty else 0
        return _box_value(str(count), t("results", "avg_words_subtitle").format(n=avg))


    @render.ui
    def loc_short_answers_share():
        return ui.markdown(f"**{t('results', 'short_answers_share')}**")


    @render.ui
    def short_answers_share():
        req(analysis_state.get(), transcript_data.get() is not None)
        teacher = input.name_teacher() or t("analysis", "name_teacher_var")
        turns = _parse_turns(transcript_data.get(), teacher)
        pupil_lengths = [len(utt.split()) for spk, utt in turns if spk != teacher]
        if not pupil_lengths:
            return _box_value("—")
        short = sum(1 for n in pupil_lengths if n <= 3)
        pct = round(short / len(pupil_lengths) * 100, 1)
        return _box_value(f"{pct} %", f"{short} / {len(pupil_lengths)}")


    # Anzeige der Qualitativen Analyse
    @render.ui
    def loc_qualitative_analysis():
        return ui.span(t("results", "section_qualitative_analysis"))


    # Quick Stats
    @render.ui
    def loc_impulses_count():
        return ui.p(t("results", "impulses_count"))


    @render.ui
    def loc_coded_impulses():
        return ui.p(t("results", "coded_impulses"))


    # Display the number of impulses coded
    @render.text
    def teacher_impulses_coded():
        req(analysis_llm_state.get(), analysis_state.get())
        df = qual_stats_df.get()
        if df is None or df.empty:
            return "0"
        # Exclude uncoded turns (empty Shortcode from the LEFT JOIN in
        # make_qualitative_stats_df) — same filter as code_most_used.
        codes = df[t("report", "shortcode")].astype(str).str.strip()
        return int((codes != "").sum())


    @render.ui
    def loc_most_frequent_codes():
        return ui.p(t("results", "most_frequent_codes"))

    # Display the most used code
    @render.text
    def code_most_used():
        req(analysis_llm_state.get(), analysis_state.get())
        # Find the most used code
        try:
            df = qual_stats_df.get()
            if df is None or df.empty:
                return t("system_prompts", "no_code")
            # Exclude uncoded turns (empty Shortcode from the LEFT JOIN in
            # make_qualitative_stats_df) — otherwise "" usually wins the mode().
            codes = df[t("report", "shortcode")].astype(str).str.strip()
            codes = codes[codes != ""]
            if codes.empty:
                return t("system_prompts", "no_code")
            most_used_codes = codes.mode().to_list()
            return ', '.join(most_used_codes) if most_used_codes else t("system_prompts", "no_code")
        except Exception:
            return t("system_prompts", "no_code")


    @render.ui
    def loc_teacher_talking_rate():
        return ui.p(t("results", "teacher_talking_rate"))


    # Display the share of words spoken by teacher vs. students,
    # plus an expandable popover with a per-student breakdown.
    @render.ui
    def teacher_share_ui():
        req(stats.get() is not None and not stats.get().empty)
        df = stats.get()
        total_words = df['Gesamt_Woerter'].sum()
        teacher_name = input.name_teacher()

        tw = df.loc[df['Sprecher'] == teacher_name, 'Gesamt_Woerter']
        teacher_words = tw.values[0] if not tw.empty else 0

        sw = df.loc[df['Sprecher'] == "Schüler:innen", 'Gesamt_Woerter']
        student_words = sw.values[0] if not sw.empty else 0

        if total_words <= 0:
            return ui.span("0 %")

        t_share = round(teacher_words / total_words * 100, 1)
        s_share = round(student_words / total_words * 100, 1)

        teacher_label = t("results", "teacher")
        students_label = t("results", "students")

        # Per-student breakdown for the popover.
        per_speaker_df = stats_per_speaker.get()
        details_rows = []
        if per_speaker_df is not None and not per_speaker_df.empty:
            # Teacher row first.
            t_row = per_speaker_df.loc[per_speaker_df['Sprecher'] == teacher_name]
            if not t_row.empty:
                w = int(t_row['Gesamt_Woerter'].values[0])
                pct = round(w / total_words * 100, 1) if total_words > 0 else 0
                details_rows.append((teacher_label, w, pct))
            # Each student, sorted by speaker label (S01, S02, ...).
            student_rows = per_speaker_df.loc[per_speaker_df['Sprecher'] != teacher_name].sort_values('Sprecher')
            for _, r in student_rows.iterrows():
                w = int(r['Gesamt_Woerter'])
                pct = round(w / total_words * 100, 1) if total_words > 0 else 0
                details_rows.append((str(r['Sprecher']), w, pct))

        # Build the popover body: a compact, scrollable table.
        table_rows = [
            ui.tags.tr(
                ui.tags.th(t("results", "speaker"), style="text-align:left; padding:2px 8px;"),
                ui.tags.th(t("results", "words_total"), style="text-align:right; padding:2px 8px;"),
                ui.tags.th("%", style="text-align:right; padding:2px 8px;"),
            )
        ]
        for label, w, pct in details_rows:
            table_rows.append(
                ui.tags.tr(
                    ui.tags.td(label, style="text-align:left; padding:2px 8px;"),
                    ui.tags.td(f"{w}", style="text-align:right; padding:2px 8px;"),
                    ui.tags.td(f"{pct} %", style="text-align:right; padding:2px 8px;"),
                )
            )
        details_table = ui.tags.div(
            ui.tags.table(*table_rows, style="font-size:0.85rem; border-collapse:collapse; width:100%;"),
            style="max-height:300px; overflow-y:auto;",
        )

        summary = ui.tags.span(
            f"{teacher_label}: {t_share} % | {students_label}: {s_share} %",
            style="font-size:0.95rem;",
        )
        details_btn = ui.tags.span(
            ui.popover(
                ui.tags.a("Details ▾", href="#", style="font-size:0.8rem; margin-left:0.5rem; text-decoration:underline; cursor:pointer;"),
                details_table,
                title=t("results", "teacher_talking_rate"),
                placement="bottom",
            )
        )
        return ui.tags.div(summary, details_btn)


    # Qualitative Statistics Plot for Coded Impulses
    @render.ui
    def loc_impulses_distribution():
        ui.p(t("results", "impulses_distribution"))


    # Create a bar plot for qualitative statistics
    @reactive.calc
    def make_qualitative_stats_plot():
        req(llm_analysis_data.get())
        mode = resolve_mode(input)
        # Reuse the merged DataFrame from make_qualitative_stats_df so the
        # bar plot stays consistent with the table: same hierarchy resolution,
        # same multi-coding aggregation. With multi-coding ON cells contain
        # "RE; A; CO" which we split + explode below so each code is counted
        # individually.
        merged_df = make_qualitative_stats_df()
        if merged_df is None or merged_df.empty:
            _, ax = _no_data_fig(t("results", "no_data"), mode)
            qual_plot.set(ax)
            return ax
        shortcode_col = t("report", "shortcode")
        plot_df = merged_df.copy()
        plot_df[shortcode_col] = plot_df[shortcode_col].astype(str).str.strip()
        # Split multi-coded cells. For single-coding cells the regex returns
        # a single-element list, so explode is a no-op.
        plot_df[shortcode_col] = plot_df[shortcode_col].str.split(r"\s*;\s*", regex=True)
        plot_df = plot_df.explode(shortcode_col)
        plot_df[shortcode_col] = plot_df[shortcode_col].astype(str).str.strip()
        plot_df = plot_df[plot_df[shortcode_col] != ""]
        if plot_df.empty:
            _, ax = _no_data_fig(t("results", "no_data"), mode)
            qual_plot.set(ax)
            return ax
        analysis_plot = plot_df.groupby(shortcode_col).agg(
            Anzahl=(shortcode_col, 'count'),
            ).reset_index().plot(
                kind='bar', x=shortcode_col, y='Anzahl',
                alpha=1, rot=0, width=0.55, color=primary_color(mode),
            )
        analysis_plot.set_xlabel(t("report", "shortcode"))
        # Rotate tick labels without resetting ticks (avoids FixedLocator/labels mismatch)
        plt.setp(analysis_plot.get_xticklabels(), rotation=45, ha='right')
        analysis_plot.set_ylabel(t("report", "quantity"))
        legend = analysis_plot.get_legend()
        if legend is not None:
            legend.remove()
        for container in analysis_plot.containers:
            analysis_plot.bar_label(container, label_type='edge')
        round_bar_corners(analysis_plot)
        apply_axes_style(analysis_plot, mode)
        qual_plot.set(analysis_plot)
        return analysis_plot


    # Plot für qualitative Statistik
    @render.plot(alt="Noch keine Daten", height=260)
    def qualitative_stats_plot():
        if not llm_analysis_data.get():
            fig, _ = _no_data_fig(t("results", "no_data"), resolve_mode(input))
            return fig
        else:
            return make_qualitative_stats_plot()


    @render.ui
    def loc_over_time_quali_title():
        return ui.span(t("results", "over_time_quali_title"))


    @reactive.calc
    def make_qualitative_stats_over_time_plot():
        req(llm_analysis_data.get())
        req(transcript_data.get() is not None)
        mode = resolve_mode(input)
        latest_df = llm_analysis_data.get()[-1]
        if latest_df is None or latest_df.empty:
            _, ax = _no_data_fig(t("results", "no_data"), mode)
            return ax
        transcript = transcript_data.get()
        teacher = input.name_teacher() or t("analysis", "name_teacher_var")
        n_segments = 3
        labels = _segment_labels_for(n_segments)
        mapped = map_impulses_to_turn_index(latest_df, transcript, teacher)
        total_turns = count_transcript_turns(transcript, teacher)
        dist = code_distribution_over_time(
            mapped, total_turns,
            n_segments=n_segments,
            segment_labels=labels,
        )
        if dist.empty:
            _, ax = _no_data_fig(t("results", "no_data"), mode)
            return ax
        pivot = (dist.pivot(index="Abschnitt", columns="Shortcode", values="Anteil")
                     .fillna(0)
                     .reindex(labels))
        ax = pivot.plot(
            kind='bar', stacked=True, rot=0, alpha=1, width=0.55,
            color=stack_colors(mode, len(pivot.columns)),
        )
        ax.set_xlabel(t("results", "section"))
        ax.set_ylabel(t("results", "share"))
        ax.set_ylim(0, 1)
        ax.legend(loc="upper right", fontsize=8, title=t("report", "shortcode"),
                  bbox_to_anchor=(1.0, 1.0))
        apply_axes_style(ax, mode)
        return ax

    state.make_qualitative_stats_over_time_plot = make_qualitative_stats_over_time_plot


    @render.plot(alt="placeholder", height=240)
    def qualitative_stats_over_time_plot():
        if not llm_analysis_data.get():
            fig, _ = _no_data_fig(t("results", "no_data"), resolve_mode(input))
            return fig
        return make_qualitative_stats_over_time_plot()


    # DataFrame of Coded Impulses
    @render.ui
    def loc_impulses_coding():
        return ui.span(
            t("results", "impulses_coding"),
            ui.tags.small(
                " — ", t("results", "edit_code_hint"),
                class_="text-muted",
            ),
        )


    # Create a DataFrame for qualitative statistics
    @reactive.calc
    def make_qualitative_stats_df():
        req(llm_analysis_data.get())
        analysis_df = llm_analysis_data.get()[-1].copy()
        cols = ['#', t("report", "speaker"), t("report", "teacher_statement"), t("report", "shortcode")]
        # Empty analysis (no codable turns) -> return empty, properly-named df
        if analysis_df.empty:
            empty_df = pd.DataFrame(columns=cols)
            qual_stats_df.set(empty_df)
            return empty_df
        # Back-fill Sprecher column if missing (older sessions)
        if "Sprecher" not in analysis_df.columns:
            analysis_df["Sprecher"] = ""

        transcript_text = transcript_data.get()
        if not transcript_text:
            # Fallback: converted transcript (format wizard result)
            conv = converted_transcript.get()
            if conv and conv.get("text"):
                transcript_text = conv["text"]
        if transcript_text:
            teacher_name = input.name_teacher() or t("analysis", "name_teacher_var")
            turns = _parse_turns(transcript_text, teacher_name)
            all_turns_df = pd.DataFrame(turns, columns=["Sprecher", "Impuls"])
            # Normalize parsed speaker to canonical teacher_name (case-insensitive
            # regex may produce the verbatim transcript casing, e.g. "Lehrer" vs "LEHRER").
            all_turns_df["Sprecher"] = all_turns_df["Sprecher"].apply(
                lambda s: teacher_name if s.lower() == teacher_name.lower() else s
            )
            all_turns_df['#'] = range(1, len(all_turns_df) + 1)
            # Build a tolerant merge key: lowercase, strip surrounding punctuation
            # and collapse internal whitespace. LLMs frequently return Impulse
            # text with minor edits (trimmed trailing periods, normalized
            # quotes, collapsed whitespace) — exact-match on the raw string
            # would leave every Shortcode cell empty for real-LLM runs.
            def _norm_impuls(s):
                t_ = re.sub(r"\s+", " ", str(s)).strip()
                return re.sub(r"^[\s\"'„“”»«()\[\]\.…!?,:;-]+|[\s\"'„“”»«()\[\]\.…!?,:;-]+$", "", t_).lower()
            all_turns_df["__key__"] = all_turns_df["Sprecher"] + " :: " + all_turns_df["Impuls"].apply(_norm_impuls)
            coded = analysis_df[["Sprecher", "Impuls", "Shortcode"]].copy()
            # Normalize teacher speaker name: LLMs sometimes return "Lehrperson" or
            # "Lehrer" even when the transcript uses the configured teacher_name (e.g.
            # "LEHRER"). Map any case-insensitive match to the canonical name so the
            # join key aligns with all_turns_df.
            _teacher_aliases = {"lehrperson", "lehrer", "lehrkraft", "teacher", teacher_name.lower()}
            coded["Sprecher"] = coded["Sprecher"].apply(
                lambda s: teacher_name if str(s).lower() in _teacher_aliases else s
            )
            coded["__key__"] = coded["Sprecher"] + " :: " + coded["Impuls"].apply(_norm_impuls)
            # Hierarchie aus dem Codebuch ableiten (Position oder explizite
            # Priorität-Spalte). Codes ausserhalb des Codebuchs landen ans Ende.
            _priority_lookup = build_priority_lookup(codebook_data.get())
            coded["__priority__"] = coded["Shortcode"].apply(
                lambda c: priority_for(_priority_lookup, str(c).strip())
            )
            # Stabiler Sort: nach Priorität (aufsteigend = höhere Priorität zuerst).
            coded = coded.sort_values("__priority__", kind="mergesort")
            if _is_multi_coding_on(input):
                # Mehrfach-Codierung: Codes pro Turn in Priorität-Reihenfolge
                # mit "; " verbinden. Doppelte Codes pro Turn werden dedupliziert
                # (dict.fromkeys behält Reihenfolge).
                coded = (
                    coded.groupby("__key__", sort=False)
                         .agg({"Shortcode": lambda s: "; ".join(dict.fromkeys(str(c).strip() for c in s if str(c).strip()))})
                         .reset_index()
                )
            else:
                # Single-Coding: höchstpriore Code überlebt pro Turn.
                coded = coded.drop_duplicates(subset=["__key__"], keep="first")
                coded = coded.drop(columns=["__priority__"])
            merged = pd.merge(
                all_turns_df,
                coded[["__key__", "Shortcode"]],
                on="__key__",
                how="left",
            )
            merged = merged.drop(columns=["__key__"])
            merged = merged[['#', 'Sprecher', 'Impuls', 'Shortcode']].copy()
            merged["Shortcode"] = merged["Shortcode"].fillna("").astype(str)
            merged.columns = cols
            # Human-in-the-loop: apply manual code corrections
            _edits = code_edits.get()
            if _edits:
                _num_col, _sc_col = cols[0], cols[3]
                for _turn, _code in _edits.items():
                    _mask = merged[_num_col] == _turn
                    if _mask.any():
                        merged.loc[_mask, _sc_col] = _code
            qual_stats_df.set(merged)
            return merged
        else:
            # Fallback: just coded impulses (no transcript available)
            analysis_df['#'] = analysis_df.reset_index().index + 1
            analysis_df = analysis_df[['#', "Sprecher", "Impuls", "Shortcode"]]
            analysis_df.columns = cols
            # Human-in-the-loop: apply manual code corrections
            _edits = code_edits.get()
            if _edits:
                _num_col, _sc_col = cols[0], cols[3]
                for _turn, _code in _edits.items():
                    _mask = analysis_df[_num_col] == _turn
                    if _mask.any():
                        analysis_df.loc[_mask, _sc_col] = _code
            qual_stats_df.set(analysis_df)
            return analysis_df


# DataFrame für qualitative Statistik generieren (editable DataGrid)
    @render.data_frame
    def qualitative_stats_df_grid():
        df = make_qualitative_stats_df()
        shortcode_col = t("report", "shortcode")
        sc_idx = list(df.columns).index(shortcode_col) if shortcode_col in df.columns else -1
        return render.DataGrid(
            df,
            editable=True,
            filters=False,
            width="100%",
            height="400px",
            styles=[
                # Highlight editable Shortcode column
                {
                    "cols": [sc_idx] if sc_idx >= 0 else [],
                    "style": {"background-color": "var(--bs-primary-bg-subtle, #cfe2ff)"},
                },
            ],
        )

    @qualitative_stats_df_grid.set_patch_fn
    def _(*, patch):
        """Validate cell edits: only Shortcode column, only valid codebook codes."""
        df = make_qualitative_stats_df()
        shortcode_col = t("report", "shortcode")
        sc_col_idx = list(df.columns).index(shortcode_col) if shortcode_col in df.columns else -1

        # Reject edits to non-Shortcode columns
        if patch["column_index"] != sc_col_idx:
            return df.iloc[patch["row_index"], patch["column_index"]]

        new_code = str(patch["value"]).strip()
        # Allow clearing a code (empty string)
        if not new_code:
            turn_num = int(df.iloc[patch["row_index"], 0])
            edits = dict(code_edits.get())
            edits[turn_num] = ""
            code_edits.set(edits)
            return ""

        # Validate against codebook
        valid_codes = set(build_priority_lookup(codebook_data.get()).keys())
        if new_code not in valid_codes:
            ui.notification_show(
                t("results", "edit_code_invalid").format(
                    code=new_code,
                    valid=", ".join(sorted(valid_codes)),
                ),
                type="warning",
                duration=5,
            )
            return df.iloc[patch["row_index"], sc_col_idx]

        # Store the edit
        turn_num = int(df.iloc[patch["row_index"], 0])
        edits = dict(code_edits.get())
        edits[turn_num] = new_code
        code_edits.set(edits)
        return new_code


    # DataFrame für qualitative Statistik
    @render.ui
    def quali_stats_df():
        if not llm_analysis_data.get():
            return ui.output_plot("placeholder")
        else:
            return ui.output_data_frame("qualitative_stats_df_grid")


    # Placeholder Plot, wenn noch keine Daten vorhanden sind
    @render.plot(alt="Noch keine Daten")
    def placeholder():
        fig, _ = _no_data_fig(t("results", "no_data"), resolve_mode(input))
        placeholder_plot.set(fig)
        return fig


    @render.plot(alt="Noch keine Daten")
    def placeholder2():
        return placeholder_plot.get()


    # Code-Legende aus Codebuch extrahieren — Code + Bezeichnung,
    # damit der Leser nicht raten muss wofür "Q1" steht.
    @reactive.effect
    def extract_code_legend():
        data = codebook_data.get()
        req(data != None)
        if isinstance(data, list):
            df = pd.DataFrame(data)
            code_col = df.columns[0]
            # Zweite Spalte (Bezeichnung/Label) ist optional — manche
            # Codebücher haben nur Codes ohne Label.
            label_col = df.columns[1] if len(df.columns) > 1 else None
            seen = set()
            entries = []
            for _, row in df.iterrows():
                code = str(row[code_col]).strip()
                if not code or code in seen:
                    continue
                seen.add(code)
                if label_col is not None:
                    label = str(row[label_col]).strip()
                    entries.append(f"{code}: {label}" if label else code)
                else:
                    entries.append(code)
            code_legend_storage.set("; ".join(entries))
        else:
            code_legend_storage.set(str(data))


    # Code-Legende anzeigen
    @render.ui
    def code_legend():
        return ui.markdown(f"**{t("results", "caption")}:** {code_legend_storage.get()}")


    # Code-Übergänge ------------------------------------------------------
    # Markov-artige Übergangsmatrix über aufeinanderfolgende codierte
    # Beiträge. Macht Dialogdynamik sichtbar, die in der reinen
    # Häufigkeitsverteilung verschwindet (z.B. IRE-Muster: Frage → Antwort
    # → Feedback). Reagiert auf alle Inputs, die qual_stats_df beeinflussen.
    @reactive.calc
    def make_transition_data():
        req(llm_analysis_data.get())
        df = make_qualitative_stats_df()
        if df is None or df.empty:
            return [], pd.DataFrame(), 0
        shortcode_col = t("report", "shortcode")
        return build_transition_matrix(df, shortcode_col, normalize=True)


    @render.plot(alt="placeholder", height=320)
    def transition_heatmap_plot():
        if not analysis_llm_state.get():
            fig, _ = _no_data_fig(t("results", "no_data"), resolve_mode(input))
            return fig
        codes, mat, n_pairs = make_transition_data()
        mode = resolve_mode(input)
        if not codes or n_pairs == 0:
            fig, _ = _no_data_fig(t("results", "transitions_no_data"), mode)
            return fig
        # Dunkler Modus: invertierte Heatmap-Farben passender; light bleibt blau.
        cmap = "Greens" if mode == "dark" else "Blues"
        fig, ax = plt.subplots()
        plot_transition_heatmap(mat, ax, cmap_name=cmap)
        apply_axes_style(ax, mode)
        # apply_axes_style entfernt evtl. die Spines; Tick-Labels sind aber
        # für die Lesbarkeit der Heatmap essentiell — explizit reaktivieren.
        ax.tick_params(labelleft=True, labelbottom=True)
        return fig


    @render.ui
    def loc_transitions_title():
        return ui.span(t("results", "transitions_title"))


    @render.ui
    def loc_transitions_intro():
        return ui.tags.p(t("results", "transitions_intro"), class_="text-muted small")


    @render.ui
    def transitions_n_pairs_box():
        if not analysis_llm_state.get():
            return ui.span("—")
        try:
            _codes, _mat, n_pairs = make_transition_data()
        except Exception:
            n_pairs = 0
        return ui.tags.span(f"{t('results', 'transitions_n_pairs')}: {n_pairs}")


    # Methodentext für Paper ----------------------------------------------
    # Auto-generierter Absatz, den Forschende direkt in den Methodenteil
    # ihres Manuskripts kopieren können. Reagiert auf Sprachwechsel und
    # auf jede Aktualisierung der Analyse-Eingaben.
    def _methods_text_value() -> str:
        df = qual_stats_df.get()
        if df is not None and not df.empty:
            shortcode_col = t("report", "shortcode")
            codes = df[shortcode_col].astype(str).str.strip() if shortcode_col in df.columns else pd.Series(dtype=str)
            n_imp = len(df)
            n_cod = int((codes != "").sum()) if len(codes) else 0
        else:
            n_imp = teacher_impulses_count.get() or 0
            n_cod = 0

        # Prompts: customised wenn vom Standard abweichend
        try:
            prompts = state.config.get_prompts()
            sys_now = state.system_prompt.get() or prompts.get("system", "")
            user_now = state.user_prompt.get() or prompts.get("user", "")
            customised = (
                str(sys_now).strip() != str(prompts.get("system_default", "")).strip()
                or str(user_now).strip() != str(prompts.get("user_default", "")).strip()
            )
        except Exception:
            customised = False

        try:
            fp = compute_fingerprint(
                codebook_data.get(),
                state.effective_system_prompt() if state.effective_system_prompt else "",
                state.effective_user_prompt() if state.effective_user_prompt else "",
                state.model.get() or "",
                transcript_data.get(),
            )
        except Exception:
            fp = ""

        try:
            num_pupils = int(input.num_pupils()) if input.num_pupils() else 0
        except Exception:
            num_pupils = 0

        return build_methods_text(
            lang=state.current_lang.get(),
            model=state.model.get() or "",
            codebook=codebook_data.get(),
            num_pupils=num_pupils,
            num_participants=num_participants.get() or 0,
            num_impulses=n_imp,
            num_coded=n_cod,
            fingerprint=fp,
            prompts_customised=customised,
        )


    @render.ui
    def loc_methods_title():
        return ui.span(t("results", "methods_title"))


    @render.ui
    def methods_panel():
        if not analysis_state.get():
            return ui.tags.p(
                t("results", "no_data"),
                class_="text-muted",
            )
        try:
            text = _methods_text_value()
        except Exception as e:
            print(f"[METHODS] generation failed: {e}")
            return ui.tags.p(t("results", "no_data"), class_="text-muted")
        # Inline JS: copy the textarea into the clipboard. We use a fixed DOM id
        # so the button can locate the textarea without a Shiny round-trip; the
        # readonly textarea + button pattern works in every desktop and webview
        # browser the app targets, including the embedded pywebview window.
        copy_label = t("results", "methods_copy")
        copied_label = t("results", "methods_copied")
        failed_label = t("results", "methods_copy_failed")
        # JS escaping: the labels are ours (no user input), but escape just in
        # case translators add a quote or backslash later.
        def _js_str(s):
            return (s or "").replace("\\", "\\\\").replace("'", "\\'")
        copy_js = (
            "(function(btn){"
            "var ta=document.getElementById('methods_text_box');"
            "if(!ta){return;}"
            "var orig=btn.innerText;"
            "var done=function(ok){btn.innerText=ok?'" + _js_str(copied_label) + "':'" + _js_str(failed_label) + "';"
            "setTimeout(function(){btn.innerText=orig;},1800);};"
            "if(navigator.clipboard&&navigator.clipboard.writeText){"
            "navigator.clipboard.writeText(ta.value).then(function(){done(true);},function(){"
            "ta.select();try{document.execCommand('copy');done(true);}catch(e){done(false);}});"
            "}else{ta.select();try{document.execCommand('copy');done(true);}catch(e){done(false);}}"
            "})(this)"
        )
        return ui.tags.div(
            ui.tags.p(t("results", "methods_intro"), class_="text-muted"),
            ui.tags.textarea(
                text,
                id="methods_text_box",
                rows=6,
                readonly=True,
                class_="form-control",
                style="font-family:inherit;font-size:0.95rem;width:100%;",
            ),
            ui.tags.div(
                ui.tags.button(
                    icon_svg("copy"), " ", copy_label,
                    type="button",
                    class_="btn btn-sm btn-primary mt-2",
                    onclick=copy_js,
                ),
                style="text-align:right;",
            ),
        )
