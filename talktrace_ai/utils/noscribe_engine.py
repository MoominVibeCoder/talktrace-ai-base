"""talktrace_ai.utils.noscribe_engine — local noScribe transcription engine.

Manages an isolated noScribe installation (GPL-3.0 upstream) that TalkTrace
invokes strictly as a subprocess — no import, no linking, no bundling. The
engine lives in its own directory with its own uv-managed CPython 3.10 venv
so the ~2 GB torch/pyannote stack never touches the TalkTrace environment
(or the PyInstaller exe). Design + Phase-0 findings:
docs/noscribe-module-plan.md.

Public API (all sync; generators are meant to be driven through
``llm_analysis._stream_bridge.async_stream`` from the UI layer):

    detect() -> EngineStatus
    install_engine(_cancel_token=None)        # generator of event dicts
    run_transcription(audio_path, ...)        # generator of event dicts
    renumber_speakers(text) -> str            # S00: -> S01: ...
    uninstall_engine() -> None

Event protocol (mirrors the LLM streaming events):

    {"type": "phase",    "key": "...", "label": "..."}
    {"type": "progress", "value": 0-100 | None, "detail": "..."}
    {"type": "log",      "line": "..."}            # user-visible only
    {"type": "done",     ...}                      # payload varies
    {"type": "error",    "message": "...", "log_tail": [...]}
    {"type": "cancelled"}

This module is intentionally stdlib-only and imports nothing from
talktrace_ai, so it can be smoke-tested standalone:

    python -m talktrace_ai.utils.noscribe_engine detect
    python -m talktrace_ai.utils.noscribe_engine install
    python -m talktrace_ai.utils.noscribe_engine transcribe <audio> [de] [2]
    python -m talktrace_ai.utils.noscribe_engine uninstall
"""
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

# --------------------------------------------------------------------------
# Pinned versions — change deliberately, re-run the Phase-0 smoke chain after.
# --------------------------------------------------------------------------

# uv bootstrap binary (static exe, no Python needed). Release tags carry no
# "v" prefix. The .sha256 asset from the same release guards the download
# against corruption/truncation.
UV_VERSION = "0.11.19"
UV_ASSET = "uv-x86_64-pc-windows-msvc.zip"
UV_URL = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{UV_ASSET}"
UV_SHA_URL = UV_URL + ".sha256"

# noScribe pinned by commit hash, not tag/branch — survives upstream tag
# deletion and force-pushes. v0.7.2 == a5b2ad9.
NOSCRIBE_TAG = "v0.7.2"
NOSCRIBE_COMMIT = "a5b2ad955d3ea5af72757b28b28e1f670ab7e12e"
NOSCRIBE_ZIP_URL = f"https://github.com/kaixxx/noScribe/archive/{NOSCRIBE_COMMIT}.zip"

# Engine Python MUST be 3.10: cpufeature 0.2.1 has no Windows wheels for
# 3.11+ and source builds need MSVC. Matches noScribe's own Dockerfile.
ENGINE_PYTHON = "3.10"

# torch family MUST stay in lockstep: pyannote.audio 4.x loads torchcodec
# DLLs that are built against exactly this torch ABI. soundfile gives
# torchaudio a WAV backend so diarization works even when the torchcodec
# DLLs can't load (no system FFmpeg) — Phase-0-verified on Windows 11.
ENGINE_DEPS = [
    "torch==2.8.*",
    "torchaudio==2.8.*",
    "torchcodec==0.7.*",
    "soundfile",
    "av",
    "AdvancedHTMLParser",
    "appdirs",
    "cpufeature",
    "customtkinter",
    "CTkToolTip",
    "faster-whisper",
    "Pillow",
    "pyannote.audio>=4.0,<5",
    "python-i18n",
    "PyYAML",
    "huggingface_hub",
]

# Whisper "fast" model (large-v3-turbo int8, ~0.8 GB). The HF repo hosts 17
# models; allow_patterns keeps the download to the one we need (4.63 GB -> 0.8 GB).
HF_MODEL_REPO = "mukowaty/faster-whisper-int8"
HF_MODEL_SUBDIR = "faster-whisper-large-v3-turbo-int8"

MIN_FREE_BYTES = 5 * 1024**3  # install pre-flight: engine + model + headroom

ENGINE_DIR_NAME = "noscribe-engine"
ENGINE_MARKER = "engine.json"
DEPS_MARKER = "deps.ok"

# Desktop-noScribe install locations (detection step 2: an existing desktop
# install is used directly and saves the ~3 GB engine download).
_DESKTOP_CANDIDATES = (
    r"%PROGRAMFILES%\noScribe\noScribe.exe",
    r"%LOCALAPPDATA%\Programs\noScribe\noScribe.exe",
)

_IS_WINDOWS = platform.system() == "Windows"


def engine_dir() -> Path:
    """%LOCALAPPDATA%\\TalkTraceAI\\noscribe-engine (per-user, no admin)."""
    if _IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "TalkTraceAI" / ENGINE_DIR_NAME


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

@dataclass
class EngineStatus:
    state: str                    # "ready" | "not_installed" | "broken"
    mode: str = "engine"          # "engine" (our venv) | "desktop" (noScribe.exe)
    engine_dir: Optional[Path] = None
    desktop_exe: Optional[Path] = None
    info: dict = field(default_factory=dict)
    detail: str = ""


def _engine_paths(root: Path) -> dict:
    return {
        "python": root / "venv" / "Scripts" / "python.exe",
        "src": root / "src",
        "main": root / "src" / "noScribe.py",
        "model": root / "src" / "models" / "fast" / "model.bin",
        "marker": root / ENGINE_MARKER,
    }


def _find_desktop_noscribe() -> Optional[Path]:
    for raw in _DESKTOP_CANDIDATES:
        p = Path(os.path.expandvars(raw))
        if p.exists():
            return p
    return None


def detect() -> EngineStatus:
    """Cheap, file-system-only detection — safe to call from render code.

    Order: own engine (healthy) > desktop noScribe > broken own engine >
    not installed. A structurally complete engine without engine.json
    (e.g. the manual Phase-0 install) is adopted: the marker is backfilled.
    """
    root = engine_dir()
    p = _engine_paths(root)
    structure_ok = all(p[k].exists() for k in ("python", "main", "model"))

    if structure_ok:
        if not p["marker"].exists():
            _write_engine_marker(root, adopted=True)
        try:
            info = json.loads(p["marker"].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            info = {}
        return EngineStatus(state="ready", mode="engine", engine_dir=root, info=info)

    desktop = _find_desktop_noscribe()
    if desktop is not None:
        return EngineStatus(state="ready", mode="desktop", desktop_exe=desktop,
                            detail=str(desktop))

    if root.exists() and any(root.iterdir()):
        return EngineStatus(state="broken", engine_dir=root,
                            detail="incomplete install — repair by re-running install")

    return EngineStatus(state="not_installed", engine_dir=root)


def _write_engine_marker(root: Path, adopted: bool = False) -> None:
    data = {
        "schema": 1,
        "noscribe_tag": NOSCRIBE_TAG,
        "noscribe_commit": NOSCRIBE_COMMIT,
        "engine_python": ENGINE_PYTHON,
        "uv_version": UV_VERSION,
        "model": "fast",
        "installed_at": datetime.now().isoformat(timespec="seconds"),
        "adopted": adopted,
    }
    (root / ENGINE_MARKER).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Subprocess plumbing
# --------------------------------------------------------------------------

def _popen_kwargs() -> dict:
    # PYTHONUNBUFFERED: the child's stdout is a pipe (block-buffered by
    # default), which delays noScribe's status lines and the pyannote
    # percentages by kilobytes — progress must arrive live and in order.
    # PYTHONIOENCODING: force utf-8 so German status text survives the
    # roundtrip on cp1252 consoles.
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    kwargs: dict = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if _IS_WINDOWS:
        # New process group so taskkill /T reaches the whole tree;
        # CREATE_NO_WINDOW keeps console flashes away from exe users.
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _kill_tree(proc: subprocess.Popen) -> None:
    """Terminate a process and all of its children (torch worker pools)."""
    if proc.poll() is not None:
        return
    if _IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _iter_output(proc: subprocess.Popen) -> Iterator[str]:
    """Yield output split on BOTH \\n and \\r.

    tqdm-style progress (HF downloads, pyannote segmentation/embeddings)
    rewrites its line with bare carriage returns; splitting only on \\n
    would withhold those percentages until the line completes.
    """
    buf: list = []
    assert proc.stdout is not None
    while True:
        ch = proc.stdout.read(1)
        if ch == "":
            break
        if ch in ("\n", "\r"):
            # rstrip only — leading whitespace marks traceback continuation
            # lines and is load-bearing for the noise filter.
            line = "".join(buf).rstrip()
            buf.clear()
            if line.strip():
                yield line
        else:
            buf.append(ch)
    tail = "".join(buf).rstrip()
    if tail.strip():
        yield tail


def _cancelled(token: Any) -> bool:
    return token is not None and token.is_cancelled()


def _start_cancel_watchdog(proc: subprocess.Popen, token: Any) -> None:
    """Kill the process tree as soon as the token fires.

    The consuming loops only see the token between output lines, but
    pyannote computes silently for minutes on CPU — a cancel must not wait
    for the next line. The watchdog polls the token and kills the tree;
    the reader loop then unblocks on stdout EOF.
    """
    if token is None:
        return

    def watch():
        while proc.poll() is None:
            if token.is_cancelled():
                _kill_tree(proc)
                return
            time.sleep(0.3)

    threading.Thread(target=watch, daemon=True).start()


def _run_step(cmd: list, cwd: Optional[Path], token: Any,
              log_tail: deque) -> Iterator[dict]:
    """Run one install step, stream its output, raise on failure.

    Yields {"type": "step_line", "line": ...} for every output fragment;
    the caller decides what is user-visible. Raises _StepFailed on
    non-zero exit, _StepCancelled if the token fires mid-run.
    """
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, **_popen_kwargs())
    _start_cancel_watchdog(proc, token)
    try:
        for line in _iter_output(proc):
            log_tail.append(line)
            yield {"type": "step_line", "line": line}
            if _cancelled(token):
                _kill_tree(proc)
                raise _StepCancelled()
        rc = proc.wait()
    finally:
        if proc.poll() is None:
            _kill_tree(proc)
    if _cancelled(token):
        # watchdog killed the process; report cancel, not failure
        raise _StepCancelled()
    if rc != 0:
        raise _StepFailed(f"{Path(cmd[0]).name} exited with code {rc}")


class _StepFailed(RuntimeError):
    pass


class _StepCancelled(Exception):
    pass


# --------------------------------------------------------------------------
# Install
# --------------------------------------------------------------------------

def _download(url: str, dest: Path, token: Any) -> Iterator[dict]:
    """Stream a file to disk, yielding percentage progress events."""
    req = urllib.request.Request(url, headers={"User-Agent": "TalkTraceAI"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        last_pct = -1
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                if _cancelled(token):
                    raise _StepCancelled()
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    if pct != last_pct:
                        last_pct = pct
                        yield {"type": "progress", "value": pct,
                               "detail": f"{done // 1024**2} / {total // 1024**2} MB"}


def _check_internet() -> bool:
    try:
        req = urllib.request.Request("https://github.com", method="HEAD",
                                     headers={"User-Agent": "TalkTraceAI"})
        urllib.request.urlopen(req, timeout=8)
        return True
    except OSError:
        return False


def _resolve_uv(root: Path, token: Any, log_tail: deque) -> Iterator[dict]:
    """Locate or bootstrap uv; yields events, finally yields {"type": "uv", "path": ...}.

    Preference: engine-local uv.exe > uv on PATH > download pinned binary
    (sha256-verified against the release's .sha256 asset).
    """
    local = root / ("uv.exe" if _IS_WINDOWS else "uv")
    if local.exists():
        yield {"type": "uv", "path": local}
        return
    on_path = shutil.which("uv")
    if on_path:
        yield {"type": "uv", "path": Path(on_path)}
        return

    if not _IS_WINDOWS:
        raise _StepFailed("automatic uv bootstrap is Windows-only in v1 — "
                          "install uv manually (https://docs.astral.sh/uv/)")
    if platform.machine() not in ("AMD64", "x86_64"):
        raise _StepFailed(f"unsupported architecture: {platform.machine()}")

    zip_path = root / UV_ASSET
    yield {"type": "log", "line": f"Downloading uv {UV_VERSION}…"}
    yield from _download(UV_URL, zip_path, token)

    expected = ""
    with urllib.request.urlopen(
        urllib.request.Request(UV_SHA_URL, headers={"User-Agent": "TalkTraceAI"}),
        timeout=30,
    ) as resp:
        expected = resp.read().decode("ascii", "replace").split()[0].lower()
    actual = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if actual != expected:
        zip_path.unlink(missing_ok=True)
        raise _StepFailed("uv download failed checksum verification — retry the install")

    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("uv.exe"):
                with zf.open(name) as src, open(local, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                break
        else:
            raise _StepFailed("uv.exe not found inside the downloaded archive")
    zip_path.unlink(missing_ok=True)
    log_tail.append(f"uv {UV_VERSION} bootstrapped at {local}")
    yield {"type": "uv", "path": local}


_PCT_RE = re.compile(r"(\d{1,3})%")


def install_engine(_cancel_token: Any = None) -> Iterator[dict]:
    """Install (or repair) the engine. Sync generator of event dicts.

    Idempotent: every step checks for its own completed artifact and skips,
    so an interrupted install resumes where it stopped (HF downloads resume
    natively). engine.json is written last — its absence marks the install
    as incomplete and detect() reports "broken".
    """
    token = _cancel_token
    root = engine_dir()
    p = _engine_paths(root)
    log_tail: deque = deque(maxlen=80)

    def fail(message: str) -> dict:
        return {"type": "error", "message": message, "log_tail": list(log_tail)}

    try:
        # -- preflight ----------------------------------------------------
        yield {"type": "phase", "key": "preflight", "label": "Checking requirements"}
        root.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(root).free
        if free < MIN_FREE_BYTES:
            yield fail(f"not enough free disk space: {free // 1024**3} GB free, "
                       f"{MIN_FREE_BYTES // 1024**3} GB required")
            return
        if not _check_internet():
            yield fail("no internet connection — the install downloads ~3 GB "
                       "from github.com and huggingface.co")
            return

        # -- uv bootstrap ---------------------------------------------------
        yield {"type": "phase", "key": "uv", "label": "Preparing installer (uv)"}
        uv = None
        for ev in _resolve_uv(root, token, log_tail):
            if ev["type"] == "uv":
                uv = ev["path"]
            else:
                yield ev
        assert uv is not None

        # -- managed Python 3.10 venv ---------------------------------------
        yield {"type": "phase", "key": "python", "label": f"Python {ENGINE_PYTHON} environment"}
        if not p["python"].exists():
            for ev in _run_step(
                [str(uv), "venv", "--python", ENGINE_PYTHON, str(root / "venv")],
                cwd=root, token=token, log_tail=log_tail,
            ):
                pass  # uv venv output is terse; tail captures it for errors

        # -- noScribe source @ pinned commit ----------------------------------
        yield {"type": "phase", "key": "noscribe", "label": f"noScribe {NOSCRIBE_TAG}"}
        if not p["main"].exists():
            zip_path = root / "noscribe-src.zip"
            yield from _download(NOSCRIBE_ZIP_URL, zip_path, token)
            extract_dir = root / "_extract"
            shutil.rmtree(extract_dir, ignore_errors=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
            # GitHub archives wrap everything in noScribe-<commit>/
            inner = next(extract_dir.iterdir())
            shutil.rmtree(p["src"], ignore_errors=True)
            shutil.move(str(inner), str(p["src"]))
            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)

        # -- pinned dependencies ----------------------------------------------
        yield {"type": "phase", "key": "deps", "label": "Engine dependencies (~2 GB)"}
        deps_marker = root / DEPS_MARKER
        if not deps_marker.exists():
            n_lines = 0
            for ev in _run_step(
                [str(uv), "pip", "install", "--python", str(p["python"]), *ENGINE_DEPS],
                cwd=root, token=token, log_tail=log_tail,
            ):
                n_lines += 1
                if n_lines % 5 == 0:
                    yield {"type": "progress", "value": None,
                           "detail": ev["line"][:100]}
            deps_marker.write_text(json.dumps(ENGINE_DEPS), encoding="utf-8")

        # -- Whisper model ------------------------------------------------------
        yield {"type": "phase", "key": "model", "label": "Whisper model „fast“ (~0.8 GB)"}
        if not p["model"].exists():
            model_dst = p["src"] / "models" / "fast"
            model_dst.mkdir(parents=True, exist_ok=True)
            dl_dir = root / "_model_dl"
            script = (
                "from huggingface_hub import snapshot_download\n"
                f"snapshot_download(repo_id={HF_MODEL_REPO!r}, "
                f"allow_patterns=[{HF_MODEL_SUBDIR + '/*'!r}], "
                f"local_dir={str(dl_dir)!r})\n"
            )
            for ev in _run_step(
                [str(p["python"]), "-c", script],
                cwd=root, token=token, log_tail=log_tail,
            ):
                m = _PCT_RE.search(ev["line"])
                if m:
                    yield {"type": "progress", "value": min(int(m.group(1)), 100),
                           "detail": "model download"}
            src_files = dl_dir / HF_MODEL_SUBDIR
            if not src_files.exists():
                raise _StepFailed("model download finished but the expected "
                                  f"directory {HF_MODEL_SUBDIR} is missing")
            for f in src_files.iterdir():
                shutil.move(str(f), str(model_dst / f.name))
            shutil.rmtree(dl_dir, ignore_errors=True)

        # -- health check --------------------------------------------------------
        yield {"type": "phase", "key": "health", "label": "Verifying installation"}
        out_lines: list = []
        for ev in _run_step(
            [str(p["python"]), "-m", "noScribe", "--help-models"],
            cwd=p["src"], token=token, log_tail=log_tail,
        ):
            out_lines.append(ev["line"])
        if not any("fast" in line for line in out_lines):
            raise _StepFailed("health check failed: noScribe does not list the "
                              "„fast“ model")

        _write_engine_marker(root)
        yield {"type": "done", "engine_dir": str(root)}

    except _StepCancelled:
        yield {"type": "cancelled"}
    except _StepFailed as exc:
        yield fail(str(exc))
    except OSError as exc:
        yield fail(f"{type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------
# Transcription
# --------------------------------------------------------------------------

# Locale-INDEPENDENT anchors. noScribe's i18n status lines arrive in the
# system language (German on the Phase-0 machine), but the CLI wrapper
# prints hard-coded English, and the library-level markers come from
# faster_whisper/pyannote logging. Only these are load-bearing:
_RE_DURATION = re.compile(r"Processing audio with duration\s+(\d+(?::\d+)+(?:\.\d+)?)")
_RE_SEGMENT = re.compile(r"Processing segment at\s+(\d+(?::\d+)+(?:\.\d+)?)")
_RE_DIARIZE_PCT = re.compile(r"(segmentation|embeddings)\D*?(\d{1,3})%")
_RE_SUCCESS = re.compile(r"Transcription completed successfully!")
_RE_FAILED = re.compile(r"Transcription (failed|canceled)")

# Non-fatal noise that fires on every successful run (Phase-0 list plus the
# torchcodec advisory block observed in the Phase-1 smoke run) — kept out of
# the user-visible log, retained in log_tail for diagnostics.
_NOISE_RE = re.compile(
    r"torchcodec|torchaudio|libtorchcodec|deprecat|degrees of freedom|"
    r"int8_float16|UserWarning|FutureWarning|warnings\.warn|"
    r"FFmpeg|PyTorch version|sequences\.std|torch\.Tensor|"
    r"^\d+\.\s|^\*|^versions? \d|^table:$|^noScribe$|"
    r"^\s+|^Traceback|^\s*File \"|DEBUG:|INFO:",
    re.IGNORECASE,
)


def _parse_clock(text: str) -> float:
    """\"MM:SS(.ms)\" or \"HH:MM:SS(.ms)\" -> seconds."""
    parts = text.split(":")
    seconds = float(parts[-1])
    for i, part in enumerate(reversed(parts[:-1]), start=1):
        seconds += int(part) * 60**i
    return seconds


_SPEAKER_LINE_RE = re.compile(r"^S(\d+):", re.MULTILINE)


def renumber_speakers(text: str) -> str:
    """Shift noScribe's zero-based speaker labels to TalkTrace's one-based.

    pyannote starts at SPEAKER_00 -> noScribe writes S00:. One pass over all
    labels (no collision: every label moves up by exactly one).
    """
    return _SPEAKER_LINE_RE.sub(
        lambda m: f"S{int(m.group(1)) + 1:02d}:", text
    )


def run_transcription(
    audio_path,
    output_path=None,
    language: str = "auto",
    speaker_detection: str = "auto",
    overlapping: bool = True,
    disfluencies: bool = True,
    _cancel_token: Any = None,
) -> Iterator[dict]:
    """Transcribe one audio file through the engine. Sync generator of events.

    `speaker_detection` is "none", "auto", or "1".."10" — small groups with
    a known size should pass the exact count (improves pyannote clustering).
    Every relevant noScribe option is passed explicitly so a stray user
    config.yml can never shadow our settings.

    The final {"type": "done"} carries `text` (speaker labels already
    renumbered S01+) and `output_path`.
    """
    token = _cancel_token
    status = detect()
    log_tail: deque = deque(maxlen=80)

    if status.state != "ready":
        yield {"type": "error", "message": f"engine not ready: {status.state}",
               "log_tail": []}
        return

    audio = Path(audio_path)
    if not audio.exists():
        yield {"type": "error", "message": f"audio file not found: {audio}",
               "log_tail": []}
        return

    if output_path is None:
        jobs = (status.engine_dir or engine_dir()) / "transcripts"
        jobs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = jobs / f"{audio.stem}-{stamp}.txt"
    out = Path(output_path)

    opts = [
        "--no-gui",
        "--language", language,
        "--model", "fast",
        "--speaker-detection", str(speaker_detection),
        "--no-timestamps",
        "--pause", "none",
        "--overlapping" if overlapping else "--no-overlapping",
        "--disfluencies" if disfluencies else "--no-disfluencies",
    ]
    if status.mode == "desktop":
        cmd = [str(status.desktop_exe), str(audio), str(out), *opts]
        cwd = status.desktop_exe.parent
    else:
        p = _engine_paths(status.engine_dir)
        cmd = [str(p["python"]), "-m", "noScribe", str(audio), str(out), *opts]
        cwd = p["src"]

    started = time.monotonic()
    phase = "setup"
    duration_s: Optional[float] = None
    saw_success = False
    saw_failure = False
    failure_detail = ""
    last_log = None

    def set_phase(new: str) -> Optional[dict]:
        nonlocal phase
        if new != phase:
            phase = new
            return {"type": "phase", "key": new, "label": new}
        return None

    yield {"type": "phase", "key": "setup", "label": "setup"}
    proc = subprocess.Popen(cmd, cwd=str(cwd), **_popen_kwargs())
    _start_cancel_watchdog(proc, token)
    try:
        for line in _iter_output(proc):
            log_tail.append(line)

            if _cancelled(token):
                _kill_tree(proc)
                out.unlink(missing_ok=True)  # partial output is worthless
                yield {"type": "cancelled"}
                return

            m = _RE_DIARIZE_PCT.search(line)
            if m:
                ev = set_phase("diarize")
                if ev:
                    yield ev
                # Two back-to-back sub-phases; show segmentation as 0-50,
                # embeddings as 50-100 so the bar never moves backwards.
                pct = min(int(m.group(2)), 100)
                half = pct // 2 + (50 if m.group(1) == "embeddings" else 0)
                yield {"type": "progress", "value": half, "detail": m.group(1)}
                continue

            m = _RE_DURATION.search(line)
            if m:
                duration_s = _parse_clock(m.group(1))
                ev = set_phase("transcribe")
                if ev:
                    yield ev
                yield {"type": "progress", "value": 0,
                       "detail": f"audio {m.group(1)}"}
                continue

            m = _RE_SEGMENT.search(line)
            if m:
                ev = set_phase("transcribe")
                if ev:
                    yield ev
                if duration_s:
                    pos = _parse_clock(m.group(1))
                    yield {"type": "progress",
                           "value": min(int(pos * 100 / duration_s), 99),
                           "detail": m.group(1)}
                continue

            # "Whisper laden" / "Loading Whisper model" both carry the brand
            # name — good enough as a locale-independent phase hint.
            if phase == "diarize" and "whisper" in line.lower():
                ev = set_phase("whisper_load")
                if ev:
                    yield ev

            if _RE_SUCCESS.search(line):
                saw_success = True
                ev = set_phase("save")
                if ev:
                    yield ev
                continue

            if _RE_FAILED.search(line):
                saw_failure = True
                continue
            if saw_failure and not failure_detail and line.startswith("Error:"):
                failure_detail = line

            if not _NOISE_RE.search(line) and line != last_log:
                # dedupe: multiprocessing workers re-import noScribe and
                # re-print its banner lines
                last_log = line
                yield {"type": "log", "line": line}

        rc = proc.wait()
    finally:
        if proc.poll() is None:
            _kill_tree(proc)

    if _cancelled(token):
        out.unlink(missing_ok=True)
        yield {"type": "cancelled"}
        return

    if rc != 0 or not saw_success or not out.exists():
        message = failure_detail or f"transcription failed (exit code {rc})"
        yield {"type": "error", "message": message, "log_tail": list(log_tail)}
        return

    text = renumber_speakers(out.read_text(encoding="utf-8"))
    out.write_text(text, encoding="utf-8")
    yield {
        "type": "done",
        "output_path": str(out),
        "text": text,
        "audio_duration_s": duration_s,
        "elapsed_s": round(time.monotonic() - started, 1),
    }


# --------------------------------------------------------------------------
# Uninstall
# --------------------------------------------------------------------------

def uninstall_engine() -> None:
    """Delete the engine directory (frees ~3 GB). Raises OSError on failure."""
    root = engine_dir()
    if not root.exists():
        return

    def _clear_readonly(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(root, onerror=_clear_readonly)


# --------------------------------------------------------------------------
# Smoke-test CLI (Phase 1) — not wired into the app
# --------------------------------------------------------------------------

def _smoke_main(argv: list) -> int:
    # cp1252 consoles choke on replacement chars in engine output
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd = argv[0] if argv else "detect"
    if cmd == "detect":
        s = detect()
        print(f"state={s.state} mode={s.mode} dir={s.engine_dir} "
              f"desktop={s.desktop_exe}\ninfo={json.dumps(s.info, indent=2)}")
        return 0
    if cmd == "install":
        for ev in install_engine():
            print(ev if ev["type"] != "error"
                  else f"ERROR: {ev['message']}\n" + "\n".join(ev["log_tail"][-20:]),
                  flush=True)
        return 0
    if cmd == "transcribe":
        audio = argv[1]
        language = argv[2] if len(argv) > 2 else "auto"
        speakers = argv[3] if len(argv) > 3 else "auto"
        for ev in run_transcription(audio, language=language,
                                    speaker_detection=speakers):
            if ev["type"] == "done":
                print(f"\nDONE {ev['output_path']} "
                      f"({ev['elapsed_s']}s for {ev['audio_duration_s']}s audio)",
                      flush=True)
                print(ev["text"][:600], flush=True)
            elif ev["type"] == "error":
                print(f"ERROR: {ev['message']}", flush=True)
                print("\n".join(ev["log_tail"][-20:]), flush=True)
            else:
                print(ev, flush=True)
        return 0
    if cmd == "uninstall":
        uninstall_engine()
        print("engine removed")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(_smoke_main(sys.argv[1:]))
