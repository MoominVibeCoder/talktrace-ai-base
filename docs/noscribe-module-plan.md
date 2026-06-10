# noScribe Transcription Module Plan

**Status:** Phase 2 complete + revised (dedicated tab, full option
parity), verified in a live app; ready for Phase 3 (polish & ship).
Drafted 2026-06-10, last revised 2026-06-10.

## Phase 2 revision 2 (2026-06-10) — editor + richer progress

After a user test of the dedicated tab, two UX additions:

- **Editable transcript field** in the Transcription tab (human-in-the-
  loop): an `input_text_area` pre-filled from the current `transcript_data`
  (read via `reactive.isolate()` so typing isn't wiped on unrelated
  re-renders, and `num_pupils` is isolated too so a group-size change on
  the Analysis tab no longer resets the form). An **Apply** button writes
  edits back into the shared `transcript_data` and re-validates the format
  — so labels / spelling can be fixed before analysis. Verified live: text
  typed in the editor + Apply shows up in the Analysis-tab transcript
  preview with a green "format valid" status.
- **Richer progress**: prominent phase title with a spinner, a **step
  X / N** counter (from an ordered phase list stored in the progress
  dict), the percentage bar, and a live **elapsed-time clock** driven by
  `reactive.invalidate_later(1)` so the user sees activity even during
  noScribe's long silent compute phases. The raw log is demoted into a
  collapsible details block (it used to dominate the view — the reason the
  old display felt like "just printed output, then suddenly done").

## Phase 2 revision (2026-06-10) — dedicated tab + full noScribe parity

Per user request the transcription UI moved from a collapsed accordion in
the Analysis tab to its **own top-level "Transcription" tab** (between
Analysis and Results), and now exposes **every option the noScribe GUI
offers**:

- audio in; output filename (saved into the engine's `transcripts/` dir,
  always `.txt` — the format the analysis consumes; prefilled from the
  audio stem)
- start / stop range (`HH:MM:SS`, validated, passed as `--start/--stop`)
- language (auto/de/en), **model (fast/precise)**, speaker detection
  (none/auto/1–10), mark-pause (none/1sec+/2sec+/3sec+), overlapping
  speech, disfluencies, timestamps
- **precise model downloaded on demand**: the dropdown flags a
  not-installed model ("precise (downloads ~1.6 GB)"); on Start, if the
  chosen model is missing it is fetched first (progress shown) and then
  transcription runs. Engine: a `MODELS` registry, `installed_models()`,
  and a public `download_model()` generator sharing the install path's
  download step. Precise source taken from noScribe's own
  `models/precise/NOSCRIBE_README.txt`: `mobiuslabsgmbh/faster-whisper-
  large-v3-turbo` (whole repo → `src/models/precise/`).

Because it's a full tab now, the section is always visible — no
output-suspension caveat. When timestamps are enabled, the saved file
keeps them; the analysis handoff strips inline timestamps so the coded
transcript stays clean. Verified live: all 13 inputs render, model
dropdown signposts the precise download, the no-audio modal works; and a
20-second `--stop` end-to-end run confirms every flag reaches noScribe
(header echoes Stop/Language/Speakers/Overlapping/Timestamps/Disfluencies/
Pause) with S01+ renumbering intact.

## Phase 2 findings (2026-06-10) — completed

UI integrated into the Analysis tab as a collapsed accordion section
"Audio transcription (local)", directly above the transcript upload
(it produces what that input consumes). New handler
`talktrace_ai/handlers/noscribe.py` drives the engine through the same
`async_stream` + `CancelToken` plumbing as the LLM streaming path; new
state fields in `state.py` (`noscribe_status`, `noscribe_engine_status`,
`noscribe_progress`, `noscribe_cancel`); EN/DE strings under a `noscribe`
localization section (44 keys, parity-checked). Verified against the
Phase-0 engine in a running app: the `ready` view renders correctly
(audio upload, language, speaker count prefilled from group size,
transcribe button, engine version, uninstall link); effects fire without
error; the no-audio-selected modal works; the handoff transform
(`_strip_noscribe_header` + `is_valid_transcript_format`) produces a
valid transcript.

Implementation notes that matter:

- **Two split outputs, not one.** `noscribe_section` depends only on
  `noscribe_status` (structural layout — renders once per state change so
  the file/select inputs aren't recreated on every tick).
  `noscribe_progress_view` depends only on `noscribe_progress` (rapid
  bar/phase/live-log updates). Folding both into one output would thrash
  the inputs during install/transcription.
- **Shiny suspends hidden outputs.** While the accordion is collapsed
  (its default), `noscribe_section` does not render — it materializes on
  first expand. This is fine: the handoff target (the transcript preview
  card) is always visible, so a finished transcription lands even if the
  section is collapsed. Trade-off: the Cancel button lives inside the
  suspended output, so cancelling requires the accordion to be open.
- **Dedicated CancelToken** (`state.noscribe_cancel`), separate from the
  LLM `cancel_token`, so a transcription cancel can never abort an LLM
  run or vice-versa.
- **Handoff** strips noScribe's metadata header (everything before the
  first `S\\d+:` line — the engine already renumbered S00→S01), sets
  `transcript_data`, and sets `transcript_format_status` from
  `is_valid_transcript_format`, so the normal analysis flow takes over.

Carried into Phase 3: NOTICE entry for the GPL-3.0 upstream, README +
FEATURES mention, GDPR doc note (audio never leaves the machine), config
persistence of last-used language/speaker choices, and a real
file-upload click-through (the preview harness can't upload a file, so
the upload→transcribe→handoff click path is the one step still verified
only at the component level, not through the browser).

---

## Phase 1 findings (2026-06-10) — completed

`talktrace_ai/utils/noscribe_engine.py` implemented as a **stdlib-only,
import-free** module (no talktrace_ai imports → standalone smoke-testable
via `python -m talktrace_ai.utils.noscribe_engine <detect|install|
transcribe|uninstall>`, and maximal GPL/AGPL separation). Sync generators
of event dicts, designed to be driven through the existing
`llm_analysis._stream_bridge.async_stream` (same `_cancel_token` duck-type
convention as the LLM providers).

Smoke-tested against the Phase-0 engine — all green:

1. **detect()** adopts a structurally complete engine without
   `engine.json` (backfills the marker with `"adopted": true`) — the
   manual Phase-0 install is recognized as ready.
2. **renumber_speakers()** `S00→S01 … S10→S11`, line-anchored, single
   pass (no collisions), mid-line "S00:" untouched.
3. **Fresh-install flow** (sandboxed, stopped before the 2-GB deps
   step): preflight → uv resolution → managed CPython 3.10 venv →
   pinned-commit source zip all work; a half-done install is detected
   as `broken` (repairable, idempotent re-run).
4. **End-to-end transcription**: all 5 phases fire in order with live
   percentages; success anchor recognized; output renumbered. 278 s for
   176 s audio ≈ 1.6× realtime on CPU.
5. **Cancel mid-diarization**: process tree killed, no orphan
   processes, partial output deleted.

Hard-won details (would bite again):

- **`PYTHONUNBUFFERED=1` is mandatory for the child.** With a pipe
  (no tty), noScribe's stdout is block-buffered: status lines and
  pyannote percentages arrive kilobytes late and out of order relative
  to stderr. `PYTHONIOENCODING=utf-8` likewise, or German umlauts
  arrive mangled on cp1252 systems.
- **A cancel watchdog thread is mandatory.** Checking the cancel token
  between output lines is not enough — pyannote computes silently for
  minutes on CPU. Without the watchdog, cancel latency was 96 s; with
  it (0.3 s token poll → `taskkill /F /T`), ~1.3 s.
- **Locale-independent parse anchors only.** noScribe's i18n status
  lines arrive in the *system* language; the load-bearing anchors are
  the hard-coded English CLI lines (`Starting transcription of`,
  `Transcription completed successfully!`, `Transcription failed`) and
  library markers (`Processing audio with duration`, `Processing
  segment at`, `segmentation:`/`embeddings:` percentages).
- **Output must be split on `\r` AND `\n`** — tqdm-style progress
  rewrites lines with bare carriage returns.
- **noScribe streams finished paragraphs as plain `S0n: …` lines** —
  free live-preview material for the Phase-2 UI.
- Multiprocessing workers re-import noScribe and re-print its banner;
  consecutive-duplicate log lines are deduped.

---

## Phase 0 findings (2026-06-10) — completed

Verified end-to-end by manual install + headless transcription on
Windows 11 (PowerShell). 2:56 min audio → 4:07 min transcription run,
exit code 0, transcript content well-formed.

### Install pinning (all required)

- **Engine Python = 3.10**, not 3.11 or 3.12. `cpufeature 0.2.1` has no
  pre-built wheels for 3.11+ on Windows; 3.12 fails with "Microsoft
  Visual C++ 14.0 or greater is required". `uv venv --python 3.10`
  works without a system Python. Matches noScribe's own Dockerfile.
- **Install method = clone + manual deps**, not `pip install git+…`.
  noScribe's `pyproject.toml` is tool-config-only and lacks
  `[project].version`, so PEP 517 install errors out.
- **Right tag is `v0.7.2`** (latest release). `v0.7.0` does not exist.
- **All torch-family packages must be pinned**:
  `torch==2.8.*`, `torchaudio==2.8.*`, `torchcodec==0.7.*`. Without
  pinning, uv pulls torch 2.12 (latest) which is incompatible with
  the torchcodec DLLs that pyannote.audio 4.x depends on. Pyannote 4
  → torchcodec → matched torch is a tight version chain; one drift
  breaks step 2 (diarization).
- **`soundfile` must be installed explicitly**. Even with pinned
  torchcodec, the bundled DLLs on Windows can't load without
  system-wide FFmpeg. `soundfile` (libsndfile) gives torchaudio a
  working WAV backend, which is what pyannote actually uses for the
  intermediate `tmp_audio.wav`. With `soundfile` present, the
  torchcodec warning is emitted but harmless.
- **Requirements file has a typo**: `pyinstaller=6.14.1` (single `=`).
  We don't need pyinstaller anyway and install deps explicitly.

### Runtime behavior

- **First speaker label = `S00:`**, not `S01:`. The TalkTrace handoff
  layer must renumber `S00 → S01`, `S01 → S02`, … (trivial regex).
- **Model directory** found automatically at `src/models/fast/`
  (relative to the cloned repo root). No env var needed.
- **Realtime factor ≈ 1.4× on CPU** with the "fast" int8 model.
  10-min audio ≈ 14-min transcription, 15-min audio ≈ 21-min.
- **Stdout format is well-defined and parseable** — see "Progress
  parsing" below.
- **Exit code 0 on success**, exit 1 on processing failure (observed
  during the torchcodec debugging).

### Non-fatal warnings to suppress in the UI

These all fire even on a successful run and must be filtered out of
the user-visible log:
- `torchcodec is not installed correctly` (full traceback) — fallback
  via soundfile/torchaudio works fine.
- `torchaudio … 2.9 deprecation` — cosmetic.
- `pyannote pooling std() … degrees of freedom` — algorithm-internal.
- `ctranslate2 … int8_float16 → int8_float32 conversion` — normal on
  CPU.

Heuristic: suppress everything except lines from noScribe's own
status output (phase markers, percent updates, "Transkription beendet",
"Gespeichert unter", final summary block).

### Progress parsing

Five UI phases, each with concrete stdout markers:

| UI phase | Trigger lines | Progress source |
|---|---|---|
| 1. Setup | `=== Warteschlange wird gestartet ===` → `Audioumwandlung…` → `Umwandlung fertig.` | indeterminate, ~5 s |
| 2. Diarisierung | `Sprecher:innen identifizieren…` + `Pyannote laden` | `segmentation: N%` and `embeddings: N%` (real percentages, two sub-phases) |
| 3. Whisper-Load | `Transkription…` + `Whisper laden` + `Sprachaktivitätserkennung…` | indeterminate, ~5–15 s |
| 4. Transkription | per segment: `DEBUG:faster_whisper:Processing segment at MM:SS` | derived from segment timestamp vs. total audio duration (we know duration from `Processing audio with duration MM:SS`) |
| 5. Speichern | `Transkription beendet.` + `Gespeichert unter: <path>` | done |

### Still open (deferred to Phase 1)

- Does noScribe read `config.yml` from the user-config dir and silently
  override CLI flags? Mitigation: we set every important option
  explicitly. If we observe drift, point `NOSCRIBE_CONFIG` (or whatever
  env var noScribe exposes) at an empty config file.
- macOS / Linux behavior — out of scope for v1.

---


Goal: integrate [noScribe](https://github.com/kaixxx/noScribe) (local
Whisper transcription + pyannote speaker diarization) as an optional,
on-demand-installed engine, so users can go **audio recording → transcript
→ LLM coding** entirely inside TalkTrace — with the transcription step
running 100 % locally (no audio ever leaves the machine).

Primary use case: **10–15 minute small-group recordings**, not full
lessons. That keeps CPU transcription times in the comfortable range
(roughly 3–10 min with the int8 "fast" model on a modern laptop CPU).

---

## Why this is feasible now

noScribe 0.7 turned the project from a GUI-only app into a scriptable
package:

- **Official CLI with headless mode** — `python -m noScribe <audio>
  <out.txt> --no-gui --language de --speaker-detection 4 …`
  (argparse in `noScribe/main.py`; documented in the README).
- **Output format = our input format** — TXT export produces
  `S01: text…` paragraphs, which is exactly the transcript format
  TalkTrace already expects. No converter needed.
- **No HuggingFace token** — the pyannote diarization models are bundled
  in the noScribe repo (CC-BY-4.0); the two Whisper variants
  (large-v3-turbo fp16 ≈ 1.6 GB "precise", int8 ≈ 0.8 GB "fast") are
  public, ungated HF repos.
- **No system ffmpeg** — audio decoding goes through PyAV wheels
  (bundled ffmpeg libs).

## License boundary

noScribe is **GPL-3.0**; TalkTrace base is AGPL-3.0. We invoke noScribe
strictly as a **separate subprocess** and do not link, import, embed, or
redistribute its code or models. The install step downloads noScribe from
upstream onto the user's machine at the user's request. This keeps both
codebases cleanly separated — no derivative work, no relicensing
questions. A short note goes into NOTICE for transparency.

---

## Architecture

### Engine isolation: dedicated environment, managed by `uv`

noScribe drags in torch 2.8 + torchaudio + pyannote (~2 GB installed).
That must never enter the TalkTrace venv, and it must also work for users
of the **standalone exe who have no Python at all**. Both problems have
the same answer:

- Download a **pinned `uv` binary** (single static ~20 MB exe from GitHub
  releases, checksum-verified) into the engine directory.
- `uv venv --python 3.10 venv` — uv fetches a managed CPython 3.10
  automatically; no system Python required. **3.10 is required**, not a
  fallback: `cpufeature` has no Windows wheels for 3.11+ and 3.12 fails
  to build from source without MSVC Build Tools. 3.10 also matches
  noScribe's own Dockerfile.
- **Clone noScribe at a pinned tag** (`v0.7.2`) into `src/` rather
  than `pip install git+…` — noScribe's `pyproject.toml` lacks a
  `project.version` field, so PEP 517 install fails.
- `uv pip install --python venv\Scripts\python.exe <deps>` — install
  the runtime dependencies explicitly. **All torch-family packages
  MUST be version-pinned**, otherwise uv grabs latest torch (2.12 at
  time of write), which is incompatible with the torchcodec DLLs that
  pyannote.audio 4.x requires:
  ```
  torch==2.8.*
  torchaudio==2.8.*
  torchcodec==0.7.*
  soundfile                     # WAV backend for torchaudio; without
                                # this, diarization fails on Windows
  av AdvancedHTMLParser appdirs cpufeature customtkinter CTkToolTip
  faster-whisper Pillow
  pyannote.audio>=4.0,<5
  python-i18n PyYAML
  huggingface_hub
  ```
  We skip pyinstaller from noScribe's requirements file (a) because we
  don't bundle, and (b) because the line has a typo (`pyinstaller=…`).
- Download the Whisper "fast" model (int8, ~0.8 GB) via
  `huggingface_hub.snapshot_download` into noScribe's model directory
  ("precise" offered as an opt-in later; download resumes on retry).

Result: identical install path for source installs and the exe. Total
disk footprint ≈ **3 GB** (engine env ~2 GB + model ~0.8 GB); we check
free disk space (≥ 5 GB) before starting.

### Engine location

`%LOCALAPPDATA%\TalkTraceAI\noscribe-engine\` (via `appdirs`, same
convention as our config):

```
noscribe-engine/
├── uv.exe                  # pinned bootstrap binary
├── venv/                   # uv-managed CPython 3.10 + torch + deps
├── src/                    # cloned noScribe repo @ pinned tag
├── models/                 # whisper model(s), HF snapshot layout
└── engine.json             # installed versions, health-check timestamp
```

### Detection order (cheap → expensive)

1. **Engine env present + healthy** (`engine.json` + `--help` smoke run)
   → ready.
2. **Desktop noScribe found** (standard install paths, e.g.
   `%PROGRAMFILES%\noScribe\noScribe.exe`) → use it directly via
   `noScribe.exe … --no-gui`; skip our install entirely (saves ~3 GB for
   existing noScribe users).
3. Neither → show the install button.

### Transcription run

- Async subprocess (same pattern as our streaming LLM calls). Because
  noScribe runs from the clone, the working directory is `src/`:
  `cd src && ..\venv\Scripts\python.exe -m noScribe <audio> <out.txt>
  --no-gui --language <de|en|auto> --speaker-detection <n|auto>
  --no-timestamps --pause none`
- **Progress**: parse stdout/log lines; if unparsable, fall back to an
  indeterminate spinner + elapsed time. (Phase 0 verifies what headless
  stdout actually emits.)
- **Cancel**: red cancel button, terminates the process tree
  (`CREATE_NEW_PROCESS_GROUP` + `taskkill /T` on Windows).
- **Handoff**: on success, load the TXT into `transcript_data`, run the
  existing format check, show the green status icon — from there the
  normal analysis flow takes over. Offer the transcript as a download
  too (same pattern as the format wizard).

### Synergy detail: speaker count

Small-group recordings have a *known* participant count. The UI passes
the group size straight to `--speaker-detection <n>`, which measurably
improves pyannote's clustering vs. `auto`. Optional teacher present →
n + 1. One detail to verify in Phase 0: pyannote labels start at
`SPEAKER_00` → noScribe emits `S00`; our parser must accept `S00` or we
re-number to `S01+` during handoff (trivial regex either way).

---

## UI design

New collapsible section **"Audio transcription (local)"** in the Analysis
tab, *above* the transcript upload (it produces what that input consumes):

- **Not installed**: explainer (what gets downloaded, ~3 GB, fully local,
  GPL-3.0 upstream link) + **Install button** → modal with phase progress
  (uv → Python → noScribe → model), cancellable, resumable.
- **Installed**: audio upload (`.wav/.mp3/.m4a/.ogg/...`), language
  select, speaker count (pre-filled from group size), Start button →
  progress + cancel → on success auto-fills the transcript input.
- **Footer**: engine version + "Uninstall engine" (deletes the engine
  dir, frees the 3 GB).

State additions (`state.py`): `noscribe_status`
(`not_installed | installing | ready | running | error`),
`noscribe_progress`, `noscribe_audio_file`.

Config additions: engine path override, last-used language/speaker
options, model choice.

---

## Error taxonomy

| Failure | Handling |
|---|---|
| No internet during install | Detect early (HEAD request), friendly modal, retry button |
| Disk < 5 GB free | Pre-flight check, abort with message before downloading |
| Install interrupted | `engine.json` written last → absence marks env broken; offer repair (idempotent re-run, HF downloads resume) |
| Unsupported/corrupt audio | Surface noScribe's stderr in a modal; suggest wav/mp3 |
| Transcription exit ≠ 0 | Show tail of engine log, keep audio file, offer retry |
| Cancel mid-run | Kill process tree, delete partial output, status back to ready |
| Upstream repo/tag vanishes | We pin tag + commit hash; install uses the hash, not the branch |

---

## Phases

### Phase 0 — Spike (manual, ~half a day)
Validate the whole chain by hand on Windows before writing app code:
install noScribe per CLI docs, transcribe a 10-min fixture, confirm
(a) headless mode needs no display/interaction, (b) TXT output parses as
valid TalkTrace transcript (S00 question!), (c) what stdout emits for
progress parsing, (d) realistic CPU timing on reference hardware.
**Findings get appended to this doc; they gate the design above.**

### Phase 1 — Engine manager backend (~1–2 days) — DONE
`talktrace_ai/utils/noscribe_engine.py`: detection, uv bootstrap
(checksum-verified), pinned install, model download with progress
callbacks, health check, `run_transcription()` event generator,
process-tree cancel with watchdog, uninstall. Pure backend + smoke
tests, no UI. See "Phase 1 findings" block at top.

### Phase 2 — UI integration (~1–2 days) — DONE
Analysis-tab accordion section, inline live progress, transcription flow
with progress/cancel, handoff into `transcript_data`, status icons.
Reuses the cancel/progress patterns from the streaming LLM path. See
"Phase 2 findings" block at top. (Note: progress is shown inline in the
section rather than in a blocking modal — cleaner with the reactive
streaming model and gives a free live transcript preview.)

### Phase 3 — Polish & ship (~1 day)
EN/DE localization, config persistence, error-path walkthrough, NOTICE
note, README + FEATURES update ("Local transcription (optional noScribe
engine)"), GDPR docs update (audio never leaves the machine — strongest
selling point of the module).

### Phase 4 — Later / optional
- CUDA variant of the engine env (NVIDIA ≥ 6 GB VRAM) for ~5–10× speed
- "precise" model as selectable second engine
- macOS (Apple Silicon / MPS) — upstream supports it; mark experimental
- Linux — upstream 0.7 has known issues; wait for upstream fix
- Batch mode: queue multiple audio segments

---

## Open questions

All Phase 0 questions resolved (see "Phase 0 findings" block at top).
The one item carried into Phase 1 is the `config.yml` shadow-override
risk — handled defensively by always passing every relevant CLI flag.
