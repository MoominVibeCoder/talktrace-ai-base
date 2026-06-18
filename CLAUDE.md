# CLAUDE.md

Guidance for AI agents (and humans) working in this repository.

## What this project is

**TalkTrace AI base** is a FLOSS desktop/web app for **LLM-assisted analysis of
classroom and small-group transcripts**. It produces *quantitative* metrics
(participation, conversation shares, turn statistics) and *qualitative* coding
(speech acts via an LLM against a user codebook), and exports structured
reports. Built on [Shiny for Python](https://shiny.posit.co/py/), packaged as a
desktop app via `pywebview`, AGPL-3.0 licensed.

`base` is the public, slimmed-down distribution descended from the original
[TalkTrace-AI](https://github.com/talktrace-ai/talktrace-ai) (Leipzig
University). The stable core lives here; experimental work lives in a private
internal research fork. See [NOTICE](NOTICE) for attribution and the
relicensing history (CC BY-NC 4.0 upstream → AGPL-3.0 here, by author consent).

Two optional, self-contained modules sit alongside the core:
- **Transcription** — local audio→transcript via the standalone open-source
  engine [noScribe](https://github.com/kaixxx/noScribe), invoked **only as a
  separate subprocess** (arm's-length; not bundled, linked, or imported). Audio
  never leaves the machine.
- **Consent** — a GDPR Art. 13 consent-declaration generator (DOCX/PDF), wording
  adapted from the **CC0** [Consent-Gen-RDMO](https://github.com/berndzey/Consent-Gen-RDMO)
  (TU Dortmund). An aid, not legal advice.

## Tech stack

- **Python ≥ 3.12** (dev target 3.13). On 3.14 the embedded desktop window is
  unavailable — `pywebview` is skipped and the app opens in the default browser.
- Shiny for Python (reactive UI) · pandas / numpy · matplotlib (Agg backend) ·
  scikit-learn · python-docx + docx2pdf (PDF needs Word/COM; **not on Linux**) ·
  tiktoken · keyring (+ `keyrings.alt` on Linux).
- **LLM backends ("Big Four"):** OpenAI, Anthropic, Mistral, DeepSeek. Mistral
  and DeepSeek reuse the OpenAI SDK pointed at their endpoints.

## Run & develop

| Task | Windows | Unix |
|---|---|---|
| Run app | `start.bat` | `./start.sh` |
| Dev (autoreload) | `dev.bat` | `./dev.sh` |
| Headless (no window) | `start.bat /nowindow` | `./start.sh --nowindow` |
| Recreate venv | `start.bat /reinstall` | `./start.sh --reinstall` |

The launchers provision a `.venv/` at the repo root on first run. The app finds
a free port starting at 8000. Run from source directly with
`python -m shiny run talktrace_ai.app:app` (use the **module** path, not a file
path — a file path breaks the package-relative imports).

## Tests

pytest is configured in `pyproject.toml` (`testpaths=["tests"]`). With the
`.venv` active:

```
pytest                 # full suite
pytest tests/test_consent.py
```

Tests cover the **pure logic** modules (consent rendering, transcript
formatting/analysis, stats, fingerprint, inter-coder metrics) plus an
**import-time smoke test** (`tests/test_smoke.py`) that guards against import
breakage, `AppState` field drift, and handler-registration regressions. There
is no reactive/UI test layer — verify UI changes by running the app.

## Architecture

Thin entrypoint, handler-per-concern, strict separation of pure logic from
reactive wiring.

- **`app.py`** — builds `app_ui` (sidebar + `navset_tab` of tab builders) and a
  `server()` that does only `state = build_app_state(...)` then
  `server_body.register(state)`. Keep it thin.
- **`state.py`** — `AppState` dataclass holds all **cross-handler** reactive
  values (and a few late-bound callables like `run_analysis`). `build_app_state`
  constructs it. **Convention:** state that multiple handlers share goes in
  `AppState`; state private to one self-contained feature stays a module-local
  `reactive.value` inside that handler's `register()` (e.g. the Consent tab).
- **`handlers/`** — one module per UI section, each exposing
  `register(state)`. `handlers/server_body.py` imports and dispatches them all
  (`onboarding, sidebar, analysis, noscribe, consent, results, options, info`).
  `handlers/_common.py` is a deliberate broad re-export (`from ._common import *`)
  giving every handler the same import surface; add new shared names to its
  `__all__`.
- **`ui/`** — pure layout builders (`build_*_tab()`, `build_sidebar()`); no
  reactive logic. Localized tab titles render via `@render.text loc_title_*`
  outputs wired in the handlers.
- **`utils/`** — pure logic: `llm_analysis/` (per-provider modules +
  `_core/_json/_schema/_shared/_stream_*`), `intercoder*`, `stats`,
  `transcript_format`, `fingerprint`, `noscribe_engine`, etc.
- **`consent.py`** (top-level) — pure consent-document rendering (HTML preview,
  standalone HTML, DOCX builder).
- **`myfuncs.py`** — a thin re-export shim kept for backward-compatible import
  paths; don't add new logic here.

### Localization

UI strings live in `localization/de.py` and `localization/en.py` as
`TRANSLATIONS[lang][section][key]`. **DE and EN must stay at strict parity** —
every key added to one must be added to the other. Look strings up via
`state.t(section, key)`.

## Conventions

- **Match surrounding code** — comment density, naming, idiom. Many handler
  bodies are intentionally textually close to their pre-refactor monolith form;
  the `_common` star-import exists to preserve that.
- **Localization parity** is mandatory (see above).
- **Secrets never touch the repo or chat.** LLM API keys live in the OS keyring
  (Keychain / Credential Manager / SecretService). Any Hugging Face token used
  for model downloads stays in the HF cache — never paste it into code, config,
  or commit messages.
- **Licensing boundaries are deliberate.** noScribe stays an arm's-length
  subprocess (never import/bundle/link it). Consent wording derives from a CC0
  source. Don't introduce code that would entangle these licenses — see
  [NOTICE](NOTICE) before touching either module.
- **Commit trailer** (model-neutral):

  ```
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

- Don't add new logic to `myfuncs.py`; put it in the relevant `utils/` or
  top-level module and re-export only if an existing import path needs it.
