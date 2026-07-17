# TalkTrace AI base — Features

> What the app can do, top to bottom.

---

## Inputs

- **Transcript upload** — `.txt`, `.docx`, `.pdf`
- **Codebook upload** — `.txt`, `.docx`, `.pdf`, with live preview
- **Built-in T-SEDA codebook template** — one click (Start tile or next to the codebook upload) loads the official [T-SEDA](https://camtree.learnworlds.com/t-seda) scheme for dialogic classroom talk (T-SEDA Collective 2023, University of Cambridge, CC BY; German pack abbreviations in the DE UI, English originals in the EN UI; definitions and keywords follow the official detailed coding frame, deliberately kept concise) and presets the pipeline: LLM coding on, **teacher-only**, **multi-coding with confidence**. Just upload a transcript.
- **Multi-stage format converter** — speaker mapping, bracket/timestamp stripping, side-by-side preview before download
- **Group metadata** — class ID, class size, teacher name (all optional)

## Local audio transcription (optional)

Own **Transcription** tab — turn an audio recording into a transcript that flows straight into the analysis, **100% on-device** (the audio never leaves the machine). Powered by the standalone open-source engine [noScribe](https://github.com/kaixxx/noScribe) (Whisper + pyannote, GPL-3.0), invoked only as a separate subprocess.

- **On-demand install** — one button downloads an isolated engine (uv-managed Python + torch/pyannote + Whisper model, ~3 GB, one time); never touches the main app environment. Detects an existing desktop noScribe install and uses it instead.
- **In-app waveform trim** — drag start/end handles directly on the waveform to select the segment to transcribe; the chosen range is written to the noScribe start/stop fields automatically (no external audio editor needed). Pre-cut is performed arm's-length via the engine's own audio stack so the original file is never modified
- **Full noScribe option parity** — audio in, output filename, start/stop range, language, **model selection (fast / precise)**, speaker count (pre-filled from group size), mark-pause, overlapping speech, disfluencies, timestamps
- **Whisper model choice** — *fast* (int8, ~0.8 GB) or *precise* (fp16, ~1.6 GB); a not-yet-installed model is downloaded on demand before the run
- **Live progress** — phase, step (X of N), percentage, and an elapsed-time clock; cancellable (kills the whole process tree)
- **Editable transcript field** — fix speaker labels or spelling before analysis (human-in-the-loop); changes apply to the shared transcript that feeds the pipeline
- **Save transcript (.txt)** — download the final transcript as a plain text file, independent of the analysis pipeline
- **Session-reset aware** — *Sitzung zurücksetzen* clears the audio, the waveform widget, the trim range, and the transcript; re-uploading the same file is always re-cuttable
- **Automatic handoff** — speaker labels renumbered to the TalkTrace `S01+` convention, metadata header stripped, format validated, loaded into the Analysis tab
- **Engine management** — version shown, one-click uninstall to reclaim the disk space

## Formative teacher feedback (optional, LLM)

Own **Feedback** tab — generate **research-grounded, formative feedback for the teacher** from the analysis already on screen. Frames the report as scaffolding for self-reflection, not summative assessment.

- **Three structured axes** — *Stärken*, *Entwicklungsfelder*, *Konkrete Umsetzungshinweise*
- **Grounded in the analysis** — uses the teacher's per-code profile, the codebook definitions, and the quantitative metrics of the current session; no external context required
- **Short reference list** — anchored in dialogic-teaching literature (T-SEDA, IRE/IRF, accountable talk, productive disciplinary engagement)
- **Bilingual** — German or English prompt set, follows the active UI language
- **Editable in place** — refine, tighten, or rephrase before exporting; edits persist across re-renders
- **Export to Word (.docx) or PDF** — native document; PDF via the installed Word (docx2pdf), unavailable on Linux
- **Visible disclaimer** — formative aid, not a verdict; not a substitute for collegial or supervisory review
- **Cost tracked** — counts against the cumulative cost tracker like any other LLM call

## Consent declaration (optional)

Own **Consent** tab — generate a print-ready **GDPR Art. 13** consent declaration for the training context, where a trainer team works *with* teachers and each teacher consents to processing their **own** recording. Wording adapted from the **CC0**-licensed [Consent-Gen-RDMO](https://github.com/berndzey/Consent-Gen-RDMO) (TU Dortmund).

- **Pre-filled form + live preview** — sensible training-context defaults; the document re-renders as you edit
- **Reflects the real data flow** — local transcription (audio stays on device) vs. the configured LLM as recipient; a cloud/local toggle drives the **third-country transfer** paragraph and a separate consent checkbox, with the provider pre-filled from the active backend
- **Export to Word (.docx) or PDF** — editable native document; PDF via the installed Word (docx2pdf)
- **Required-field guards** — missing mandatory fields surface as red `!!! … !!!` markers on the document
- **Visible disclaimer** — an aid, not legal advice; shown in the form and the document footer (review by your DPO required)

## LLM backends

- **Five providers + your own custom endpoints** — [LocalMind](https://www.localmind.ai/) (EU-hosted gateway, the GDPR-friendly default), OpenAI, Anthropic, Mistral, DeepSeek, plus **any number of your own OpenAI-compatible endpoints** — add, rename and delete them in the Options tab (each with a name, base URL and its own key in the OS keyring), e.g. one self-hosted vLLM/llama.cpp server and one institutional gateway side by side. Each custom provider keeps its own model list.
- **Live model refresh** — one click per provider pulls the current model list straight from its catalogue (OpenAI-compatible `/v1/models` or Anthropic's model list; needs a saved key); embedding/audio/image models are filtered out, and prices of models already in the registry survive the refresh
- **Editable model registry** — add or remove models, set per-million-token pricing
- **Custom prompts** — edit system and user prompts, reset to default any time
- **Structured outputs with codebook enums** — Shortcode + Sprecher are decoder-side constrained to the codebook entries / transcript speakers (OpenAI strict json_schema, Anthropic tool_use input_schema, Mistral / DeepSeek / LocalMind / custom json_schema). Eliminates hallucinated codes; falls back to unconstrained schema if a model rejects the strict variant.
- **Live cost prediction** — lower-bound estimate updates as you type
- **Cumulative cost tracker** — total spend across all analyses, per provider, persisted between sessions
- **API keys in the OS keyring** — Keychain, Credential Manager, SecretService

## Quantitative results

- **Participation metrics** — class size, active participants, participation rate
- **Turn distribution plot** — words spoken by teacher vs. students
- **Per-speaker turn stats** — count, average length, median length
- **Over-time view** — three-segment breakdown across the lesson

## Qualitative results

- **Per-speaker coding** — every coded turn carries a speaker label
- **Multi-coding with confidence** — opt-in toggle; the model assigns up to **2 candidate codes per utterance, each with a 0–100 confidence** (matching T-SEDA's 0–2-codes-per-turn rule), shown in **dedicated columns** (`Code 1`, `Code 2`, e.g. `EN (92 %)`), ranked by confidence. Uncertain candidates stay visible — the confidence value makes the uncertainty transparent, the human decides. A post-processing safety net enforces the cap even if the model over-delivers; the frequency plot, most-frequent-code chip, over-time distribution and transition matrix count the **primary code** (`Code 1`) per turn so secondary candidates never skew the distribution.
- **Second review pass** — after every analysis, turns that stayed uncoded (within the selected speaker group) are automatically re-submitted to the LLM with an explicit care instruction: assign a code only if clearly supported, staying uncoded is legitimate. New codings merge into the table; a notification reports how many turns were re-checked and how many codes were added.
- **Codebook priority hierarchy** — priority line, explicit column, or codebook order
- **Code distribution plot** — frequency of each code across the conversation
- **Coded-impulse table** — every turn of the conversation (coded or not) with speaker, turn index, code column(s) and utterance text; **editable** — double-click any code cell to correct the LLM assignment (validated against the codebook, changes propagate to all plots and reports instantly; a manual edit deliberately overrides the model's confidence)
- **Over-time code distribution** — which codes emerge when in the lesson (primary code per turn, consistent with the frequency plot)
- **Code-transition heatmap** — Markov-style matrix of which code follows which (uncoded turns skipped, multi-coding takes priority-resolved code). Surfaces dialogue dynamics like IRE patterns that frequency plots hide. Optional report section in DOCX/HTML/XLSX/CSV.
- **Most-frequent-code summary** + teacher talking rate with per-student breakdown
- **Live coding view (streaming)** — codings appear progressively, opt-in toggle

## Reports

- **Four export formats** — DOCX, PDF (Win/macOS), XLSX, HTML
- **Long-format CSV / R datapack export** — stats-friendly bundle alongside DOCX/XLSX/PDF/HTML
- **Configurable sections** — quantitative, qualitative, over-time, code legend, all toggleable
- **Embedded plots and tables** — ready to share, no post-processing
- **Reproducibility fingerprint** — short hash of codebook + prompts + model + transcript, embedded in every report
- **Auto-generated methods paragraph** — copy-to-clipboard text for the methods section of papers (tool, model, codebook size, sample scope, fingerprint, date), bilingual, also embedded in the report legend

## Sessions

- **Auto-save to history** after every successful analysis
- **Manual history browser** — load, delete, save now
- **Session import/export** as `.pkl`
- **History reload is free** — no new LLM calls when restoring a saved session

## Interface

- **Start tab (landing page)** — workflow status strip, five entry tiles (T-SEDA analysis · audio · transcript · resume · demo), current-configuration line, "what's new", and the data-protection acknowledgment; the default tab on launch
- **Workflow-ordered tabs** — Start → Transcription → Analysis → Results → Feedback, with Options alongside and Consent + Info on the right; LLM configuration lives in the Analysis tab, the sidebar is organisation only (language, session save/restore/reset)
- **Light & dark themes** — Soft Nordic (light) and Deep Forest (dark), toggle in the title bar
- **Bilingual UI** — English & German, switchable any time
- **Onboarding tooltips** — hover help on every key control
- **Data-protection acknowledgment gate** — a Start-tab choice (explicit-consent data · fictive test data · only my own utterances) that must be confirmed before any LLM call goes out
- **Quickstart checklist** — live ✓/✗ panel (on the Start tab) showing what's ready
- **Demo button** — load a sample analysis without API keys (T-SEDA-coded civics lesson on lowering the voting age to 16)
- **Gold-standard self-test** — one-click *Test the app* runs a known fixture and shows expected vs. actual; trust-builder before users analyse their own data
- **Tab notification badges** — at-a-glance status of where action is needed
- **Auto tab-switch** — jumps to Results when analysis completes
- **Speaker filters** — code only the teacher, only the students, or both
- **Analysis without a teacher** — student-only group discussions fully supported
- **Cancellable analyses** — red Cancel button next to Start while a streaming run is in flight; partial codings are kept with a red banner.
- **Info / License tab** — maintainer info, GitHub/ORCID links, AGPL-3.0 notice

## Setup & launchers

- **One-click launchers** for Windows (`start.bat`), macOS, Linux (`start.sh`)
- **Auto venv + dependency install** on first run
- **Native desktop window** (Cocoa / WebKit / GTK) or headless browser mode
- **Hot-reload dev mode** (`dev.bat` / `dev.sh`)
- **Distro-aware setup** — offers to install missing packages on Debian/Fedora/Arch

---

## Roadmap

base v1 covers the stable core. Active development of new features happens in a private internal research version; reviewed, scope-appropriate additions are cherry-picked into base over time. External contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
