# Standalone Build Plan

**Status:** Plan only. No execution yet. Drafted 2026-05-26.

Goal: ship a one-click `.exe` (and later `.app` / AppImage) so end users do
not need to install Python or any dependencies. Doppelklick = App startet.

---

## Why the lift is non-trivial

The dependency stack mixes pure-Python packages with binary extensions and
runtime data files:

| Component | Bundling difficulty | Why |
|---|---|---|
| Shiny | Medium | Web server, dynamic imports, templates, static files |
| pywebview + pythonnet | Medium-High | Native deps; on Windows only on Python <3.14 |
| matplotlib | Medium | FontConfig + data files must be bundled |
| pandas / numpy / scikit-learn | Medium | Binary deps, well-supported by PyInstaller |
| tiktoken | High | Tokenizer files are downloaded/loaded at runtime |
| openpyxl, python-docx, jinja2 | Low | Pure-Python |
| keyring | Low | Uses OS-native secret store |

Realistic bundle size: **300–500 MB** (one-folder mode).

---

## Options

### 1. PyInstaller, one-folder mode  *(recommended primary path)*

- Output: `dist/TalkTraceAIbase/` containing `TalkTraceAIbase.exe`, DLLs,
  embedded Python, all libs.
- User unzips, double-clicks the `.exe`.
- Iteration cost: tiktoken + Shiny need explicit `--hidden-import` and
  `--add-data` entries; expect 3-5 rebuild cycles before the app starts.
- **Effort: 1-2 days for MVP, +1 day polish.**

### 2. PyInstaller, one-file mode

- Single `.exe`; self-extracts to temp on launch.
- Nicer UX, but slower startup (5-15 s) and more antivirus false-positives.
- **Effort: ~same as one-folder.**

### 3. Inno Setup / NSIS installer around the one-folder build

- Wraps the folder into `TalkTraceAIbase-Setup.exe`.
- Adds Start-Menu entry, uninstaller, install-path picker.
- **Effort: +4-8 h on top of a working PyInstaller build.**

### 4. Briefcase (BeeWare)

- Cross-platform app-bundling toolkit.
- Less mainstream for Shiny; fewer tutorials. Higher risk.
- **Effort: similar to PyInstaller, but more unknowns.**

### 5. "Smart launcher" (rejected)

- A small Go/C# `.exe` that downloads portable Python + deps on first run.
- Distribution = 5-10 MB, but first start needs internet and is slow.
- More moving parts to maintain. **Not recommended.**

---

## Stumbling blocks to plan for

1. **Windows Defender / SmartScreen false-positives.** PyInstaller-built
   exes are frequently flagged. Mitigation: **code-signing certificate**
   (~$80-300/year). Without it, users see the red "unknown app" warning
   on first launch.

2. **Multi-provider API keys** live in the OS keyring. Works in
   PyInstaller builds on Win/Mac out of the box; on Linux the `keyrings.alt`
   fallback already in dependencies takes over.

3. **Port conflict on 8000** — currently fails hard if the port is busy.
   For a packaged app, the launcher should detect and pick the next free
   port automatically.

4. **Updates** — either manual re-download from GitHub Releases, or
   auto-update via something like PyUpdater / custom check. Manual is
   fine for v1.

5. **Cross-platform builds** — `.exe` can only be built reliably on
   Windows, `.app` on macOS, AppImage on Linux. Practical answer:
   **GitHub Actions matrix** (`windows-latest`, `macos-latest`,
   `ubuntu-latest`). Initial setup: ~1 day. Subsequent builds are free.

6. **Python 3.14 caveat carries over.** On 3.14 the bundled build will
   also skip pywebview and fall back to the default browser. For the
   shipped exe we should bundle a known-good Python (3.13.x) and not
   leave the version to the build environment.

---

## Phased rollout

### Phase 1 — Windows MVP  *(1-2 days)*

- Write `talktrace_ai.spec` for PyInstaller (one-folder mode).
- Iterate until app launches from `dist/TalkTraceAIbase/TalkTraceAIbase.exe`.
- Manual build, distribute as ZIP via GitHub Releases.
- README addition: "Just double-click — no Python needed".

### Phase 2 — Installer  *(+1 day)*

- Inno Setup script wrapping the Phase 1 folder.
- Start-Menu entry, uninstaller, icon.
- GitHub Actions workflow that builds on tag push.

### Phase 3 — macOS / Linux  *(+1-2 days per OS)*

- macOS: py2app or PyInstaller; produces `.app` bundle.
- Linux: AppImage via `python-appimage` or PyInstaller + AppImage tooling.
- Matrix-extend the CI workflow.

### Phase 4 — Production polish

- Windows code-signing (~$80-300/year cert).
- macOS code-signing + notarization (Apple Developer Program, $99/year).
- Auto-update mechanism (optional).

---

## Open decisions for later

- **Code-signing budget.** Without it, every Phase 1-3 release will scare
  off non-technical users with browser/OS warnings. Decide before going
  public-facing.
- **Bundled Python version.** Pin to 3.13.x so `pywebview` works (no
  3.14 surprise).
- **Update mechanism.** Manual download is fine for v1; auto-update is
  worth it if updates land monthly+.
- **CI runner cost.** Free for public repos on GitHub Actions; check
  quotas if the repo ever goes private again.

---

## Effort summary

| Milestone | Effort | Cumulative |
|---|---|---|
| Phase 1: Windows MVP | 1-2 days | 1-2 days |
| Phase 2: Installer + CI | +1 day | 2-3 days |
| Phase 3: macOS + Linux | +2-4 days | 4-7 days |
| Phase 4: Code-signing + auto-update | +2-3 days + ongoing cost | 6-10 days |

"Production-grade, all three OS, signed and CI-built" is realistically
**2-3 weeks** of focused work plus ~$180-400/year in signing certificates.
