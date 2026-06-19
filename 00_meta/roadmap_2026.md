# Roadmap 2026 — Start-Tab + Sidebar-Slim

**Branch:** `redesign/start-tab-and-sidebar`
**Stand:** 2026-06-19
**Mapping:** Workflow `w7a0b7we1` (10 parallele Reader + Synthese) — Output in
`tasks/w7a0b7we1.output` (temp), Erkenntnisse hier destilliert.

---

## Vision

Heute mischt die Sidebar drei Schichten: Organisation (Sprache, Sitzung,
Reset), LLM-Konfiguration (Provider, Modell, Switches, Cost, Start-/Cancel-
Button) und eine Berichts-Aktion. Das trennen wir sauber:

- **Sidebar** = nur Organisation und Sitzungsverwaltung
- **Analyse-Tab** = LLM-Konfiguration in einer eigenen Karte
- **Results-Tab** = Berichts-Download dort, wo der Bericht entsteht
- **Neuer Start-Tab** = Default beim Öffnen. Workflow-Visualisierung,
  Einstiegs-Kacheln, Konfig-Status, Quickstart-Checkliste, „Was ist neu?",
  und das Datenschutz-Acknowledgment (statt Modal).

Jede Phase lässt die App lauffähig. Kein Sidebar-Element wird entfernt,
bevor sein Ersatz wirklich funktioniert.

---

## Phasen

### Phase 1 — Lokalisierungs-Parität + neue `start`-Sektion

**Ziel:** DE/EN strikt parallel; bestehende EN-Lücke (`system_prompts` fehlt
in `en.py`) schließen; neue `start`-Sektion in beiden Sprachen anlegen
(noch unbenutzt). Optional: Mini-Parity-Test (`set(D)==set(E)`) als billige
Versicherung gegen künftige Drift.

- **Geändert:** `talktrace_ai/localization/de.py`, `…/en.py` (+ ggf.
  `tests/test_localization_parity.py`)
- **Verifikation:** pytest + ad-hoc Parity-Check + App-Smoke-Start
- **Risiko:** sehr niedrig

### Phase 2 — Inerter Start-Tab als Schale

**Ziel:** `build_start_tab()` + `handlers/start.py` einhängen, als **letzte**
Position in `navset_tab`. Analyse bleibt Default — der Start-Tab wird erst
in Phase 6 nach vorne gezogen.

- **Neu:** `talktrace_ai/ui/start_tab.py`, `…/handlers/start.py`
- **Geändert:** `app.py`, `handlers/server_body.py`, `tests/test_smoke.py`
- **Vorlage:** identisch zum Feedback-Tab-Muster (jüngste Referenz)
- **Verifikation:** Tests grün, neuer Tab erscheint hinten, sonst keine
  Änderung sichtbar.

### Phase 3 — Start-Tab-Inhalt verdrahten (read-only)

**Ziel:** Workflow-Visualisierung (fünf Status-Pills Audio → Transkript →
Analyse → Feedback → Export), vier Einstiegs-Kacheln, Konfig-Status-Zeile,
„Was ist neu?". Alles **liest** nur — keine Sidebar-Änderung.

- **Kacheln:**
  - *Mit Audio beginnen* → Tab-Switch Transkription
  - *Mit Transkript beginnen* → Tab-Switch Analyse
  - *Letzte Sitzung laden* → öffnet History-Modal
  - *Demo ansehen* → identisch zum bestehenden Floating-Demo-Button
- **Geändert:** `handlers/start.py`, `handlers/sidebar/_session.py`
  (`_show_history_modal` als `state.show_history_modal` exponieren),
  `state.py` (späte Callable dokumentieren)
- **Verifikation:** Alle vier Kacheln navigieren korrekt; Sidebar unverändert.

### Phase 4 — LLM-Konfig-Karte im Analyse-Tab (parallel)

**Ziel:** Neue `ui.card` zwischen Document-Input (Row 2) und Vorschau-Reihe
(Row 3). **Beide** Widget-Sets (Sidebar + Karte) laufen parallel, keine
Streichung. Beide Buttons rufen denselben Helper auf.

- **Neu:** `handlers/sidebar/_analysis_card.py`
- **Geändert:** `ui/analysis_tab.py`, `handlers/sidebar/__init__.py`,
  `_analysis.py`, `_cost.py`
- **Karten-Slots:** Modell-Select, Provider-Hint, LLM-Switch, Sprecher-
  Switches, Cost-Chip, Start-/Cancel-Button, Status
- **Trick:** doppelte Input-IDs (`button_analysis` + `analysis_button_analysis`
  usw.); beide ziehen denselben Helper `state.kick_off_analysis_async`.
  `_cost.py` liest `input.llm_switch() OR input.analysis_llm_switch()`
  übergangsweise.
- **Verifikation:** beide Sets bedienen den Run; Cost-Chip aktualisiert auf
  beiden Schaltern; Demo-Lauf E2E.
- **Risiko:** mittel — doppelte IDs, leise No-Ops bei Misshandling. Manueller
  E2E zwingend bevor Phase 5 abreißt.

### Phase 5 — Bericht in Results-Tab + Sidebar verschlanken

**Ziel:** Berichts-Download in Results-Tab umziehen; alle in Phase 4
ersetzten Sidebar-Slots löschen. Sidebar reduziert sich auf:
Sprache, Sitzung-Import/Export/Verlauf/Reset.

- **Geändert:** `ui/results_tab.py`, `ui/sidebar.py`, `handlers/sidebar/_*.py`,
  `handlers/options.py:141`
- **Cleanup:**
  - `ui.update_switch("llm_switch", ...)` → `analysis_llm_switch`
  - `req(input.llm_switch(), input.button_analysis(), …)` → analysis-Varianten
  - transitorischer `_llm_on()`-Fallback in `_cost.py` entfernen
- **Verifikation:** Grep nach alten IDs leer (außer Testfixtures); E2E inkl.
  Session-Import und Reset.
- **Risiko:** mittel-hoch — stille Brüche bei vergessenen Referenzen.
  Codebase-weiter Grep zwingend.

### Phase 6 — Datenschutz aus Modal in Start-Tab + Start als Default

**Ziel:** Persistentes Acknowledgment-Widget statt Startup-Modal; neues
`AppState.data_consent_given` (initialisiert aus existierender Flag-Datei,
damit alte Nutzer nicht neu fragen müssen); `req`-Guard auf `run_analysis`
und `feedback._generate`; Quickstart-Checkliste vom Floating-Pill in den
Start-Tab; Start-Tab als **erste** Tab-Position (Default).

- **Geändert:** `state.py`, `handlers/onboarding.py`, `handlers/start.py`,
  `handlers/sidebar/_analysis.py`, `handlers/feedback.py`, `app.py`,
  `static/theme.css`, `tests/test_smoke.py`
- **CSS:** `#tt-quickstart`-Block (`position: fixed`) entfernen; Inline-
  Card-Styling; `#tt-demo-button-top` Rechts-Offset neu rechnen.
- **Verifikation:** Flag-Datei löschen → Start-Tab Default → Acknowledgment
  pending → Analyze blockt sauber via `req` → nach Bestätigung läuft Analyse
  → Neustart: Acknowledgment persistiert.
- **Risiko:** mittel — CSS-Umzug + neuer State-Field + Guards an mehreren
  Stellen.

---

## Risiken (querschnittlich)

1. **Phase 4–5: doppelte/umbenannte Input-IDs.** Vergessene Referenzen
   brechen leise. Mitigation: Codebase-weiter Grep vor Sidebar-Streichung +
   manueller E2E.
2. **Session-Import** ruft heute `ui.update_switch("llm_switch", ...)` — in
   Phase 5 mit umbenennen, sonst bleibt der Switch nach Restore unangerührt.
3. **`tt_demo_button_top` CSS-Offset** ist heute auf das Floating-Quickstart-
   Pill abgestimmt → in Phase 6 nachjustieren.
4. **Keine DE/EN-Parity-Test** existiert heute. Phase 1 fügt viele Keys
   hinzu — Mini-Test ist billige Versicherung.
5. **`navset_tab` akzeptiert `selected=` nicht** — Default-Tab via
   positionaler Reihenfolge. Phase 6 sortiert um.

---

## Offene Fragen — Vorschläge mit Default

Bestätige oder widersprich; alles ohne Widerspruch bleibt Default.

| # | Frage | Vorschlag (Default) |
|---|---|---|
| 1 | Datenschutz-Acknowledgment per Session oder persistent? | **Persistent** wie heute (Flag-Datei bleibt); zusätzliches State-Feld nur für UI-Anzeige; die getroffene Wahl (consent/fictive) im Report-Header anzeigen |
| 2 | Theme-Toggle verschieben? | **Nein, bleibt im Title-Bar** (lebt heute schon nicht in der Sidebar) |
| 3 | Berichts-Download-Position im Results-Tab? | **oben im Tab**, eigenständig (keine extra Export-Sektion) |
| 4 | „Was ist neu?" Quelle? | **statische lokalisierte Liste** in `start`-Section, manuell gepflegt (zwei Releases tief) |
| 5 | „Letzte Sitzung" → Modal oder Auto-Load? | **History-Modal** öffnen (mehr Kontrolle) |
| 6 | Quickstart verschieben oder duplizieren? | **verschieben**; Floating-Pill ersatzlos weg |
| 7 | `value=`-Kwarg für `selected=`-Default? | **Nein**, positionale Reihenfolge bleibt |
| 8 | Floating-Demo-Button erhalten? | **Behalten** als Top-Bar-Shortcut |
| 9 | Parity-Test in Phase 1 anlegen? | **Ja**, ~10 Zeilen |

---

## Verifikationsstrategie

Jede Phase wird durch dieselben drei Layer abgesichert:

1. **pytest** komplett grün (heute 89 Tests; Phase 1 fügt vermutlich +1
   Parity-Test).
2. **Import-Smoke** (`python -c "import talktrace_ai.app"`).
3. **Preview-UI**: Tab erscheint, Sprache wechselt, Reset funktioniert.

E2E mit echten LLM-Calls und realer noScribe-Transkription (Phasen 4–6)
verifiziert **Yuta** in seiner echten Umgebung — Dev-/Preview-Umgebung hat
keinen LLM-Key und keine ready-Engine
(siehe Memory `dev-env-verification-boundary`).

---

## Anhang: bewegte Sidebar-Outputs

| heutige Sidebar-ID | neuer Ort | neue Input-ID(s) |
|---|---|---|
| `loc_dynamic_model_select` | Analyse-Tab/LLM-Karte | `analysis_model_select`, `analysis_provider_select` |
| `loc_provider_hint` | Analyse-Tab/LLM-Karte | — |
| `loc_llm_switch` | Analyse-Tab/LLM-Karte | `analysis_llm_switch` |
| `loc_analyse_speakers_switches` | Analyse-Tab/LLM-Karte | `analysis_teacher_switch`, `analysis_students_switch`, `analysis_multi_coding_switch` |
| `cost_chip` | Analyse-Tab/LLM-Karte | — |
| `loc_button_analysis` | Analyse-Tab/LLM-Karte | `analysis_button_analysis` |
| `loc_button_cancel_analysis` | Analyse-Tab/LLM-Karte | `analysis_button_cancel_analysis` |
| `start_analysis` | Analyse-Tab/LLM-Karte | — |
| `show_report_download_button` | Results-Tab | (Modal-Input-ID bleibt `button_report_open`) |

**Bleiben in der Sidebar:** `language_toggle`, `loc_button_import_session`,
`loc_button_export_session`, `loc_button_history`, `loc_button_reset`.

**Bleibt im Title-Bar:** Dark-Mode-Toggle (`ui.input_dark_mode`,
`app.py:88`).
