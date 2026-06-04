# TalkTrace AI base — Features

> What the app can do, top to bottom.

---

## Inputs

- **Transcript upload** — `.txt`, `.docx`, `.pdf`
- **Codebook upload** — `.txt`, `.docx`, `.pdf`, with live preview
- **Multi-stage format converter** — speaker mapping, bracket/timestamp stripping, side-by-side preview before download
- **Group metadata** — class ID, class size, teacher name (all optional)

## LLM backends

- **Big-Four providers** — OpenAI, Anthropic, Mistral, DeepSeek
- **Editable model registry** — add or remove models, set per-million-token pricing
- **Custom prompts** — edit system and user prompts, reset to default any time
- **Structured outputs with codebook enums** — Shortcode + Sprecher are decoder-side constrained to the codebook entries / transcript speakers (OpenAI strict json_schema, Anthropic tool_use input_schema, Mistral / DeepSeek json_schema). Eliminates hallucinated codes; falls back to unconstrained schema if a model rejects the strict variant.
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
- **Multi-coding** — multiple codes per utterance, opt-in toggle
- **Codebook priority hierarchy** — priority line, explicit column, or codebook order
- **Code distribution plot** — frequency of each code across the conversation
- **Coded-impulse table** — speaker, turn index, code(s), utterance text; **editable** — double-click any Shortcode cell to correct the LLM assignment (validated against the codebook, changes propagate to all plots and reports instantly)
- **Over-time code distribution** — which codes emerge when in the lesson
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

- **Light & dark themes** — Soft Nordic (light) and Deep Forest (dark), toggleable in sidebar
- **Bilingual UI** — English & German, switchable any time
- **Onboarding tooltips** — hover help on every key control
- **Data-protection acknowledgment gate** — first-launch dialog requires active confirmation of where transcript data will be sent before any LLM call goes out
- **Quickstart checklist** — live ✓/✗ panel showing what's ready
- **Demo button** — load a sample analysis without API keys
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
