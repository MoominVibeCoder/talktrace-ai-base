# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for TalkTrace AI base — one-folder mode (Windows MVP).

Build:   pyinstaller TalkTraceAI.spec
Output:  dist/TalkTraceAI/TalkTraceAI.exe
"""
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
)

# ---------------------------------------------------------------------------
# 1.  Collect data files + hidden imports for heavy packages
# ---------------------------------------------------------------------------
# collect_all(pkg) → (datas, binaries, hiddenimports)

_packages_collect_all = [
    "shiny",
    "htmltools",
    "faicons",
    "starlette",
    "uvicorn",
    "matplotlib",
    "tiktoken",
    "tiktoken_ext",
    "certifi",          # CA bundle for HTTPS (openai / anthropic SDKs)
    "sklearn",
    "keyring",
]

all_datas = []
all_binaries = []
all_hiddenimports = []

for pkg in _packages_collect_all:
    try:
        d, b, h = collect_all(pkg)
        all_datas += d
        all_binaries += b
        all_hiddenimports += h
    except Exception:
        print(f"[WARN] collect_all('{pkg}') failed — skipping")

# ---------------------------------------------------------------------------
# 2.  Project-specific data files
# ---------------------------------------------------------------------------
# resource_path("static/…") → Path(sys._MEIPASS) / "static/…"
#   ⇒ bundle talktrace_ai/static → <_MEIPASS>/static
#
# Config: bundle ONLY default_config.ini — never the whole config/ directory.
# The developer's config.ini, cost_log.json and the .welcome_shown /
# .dataprotection_acknowledged flag files live there too; shipping them would
# leak local settings and, worse, pre-acknowledge the data-protection gate
# for every release user. ConfigManager creates a fresh config.ini from the
# default on first launch.

all_datas += [
    ("talktrace_ai/static",   "static"),
    ("talktrace_ai/config/default_config.ini", "talktrace_ai/config"),
]

# ---------------------------------------------------------------------------
# 3.  Extra hidden imports (dynamic / conditional / lazy)
# ---------------------------------------------------------------------------
all_hiddenimports += [
    # --- pywebview (desktop window) ---
    "webview",
    "clr_loader",
    "pythonnet",
    # --- keyring ---
    "keyring.backends.Windows",
    # --- LLM SDKs ---
    "openai",
    "anthropic",
    "httpx",
    "httpx._transports",
    "httpx._transports.default",
    # --- tiktoken extensions ---
    "tiktoken_ext.openai_public",
    "tiktoken_ext",
    # --- shiny internals ---
    "shiny._main",
    "shiny.session",
    # --- starlette / uvicorn internals ---
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.logging",
    # --- sklearn lazy imports ---
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
    "sklearn.metrics._pairwise_distances_reduction",
    # --- docx / openpyxl ---
    "docx",
    "openpyxl",
    # --- jinja2 ---
    "jinja2",
    # --- project modules that may be lazily imported ---
    "talktrace_ai",
    "talktrace_ai.app",
    "talktrace_ai.myfuncs",
    "talktrace_ai.paths",
    "talktrace_ai.theme",
    "talktrace_ai.state",
    "talktrace_ai.localization",
    "talktrace_ai.localization.de",
    "talktrace_ai.localization.en",
    "talktrace_ai.localization.translation",
    "talktrace_ai.examples",
    "talktrace_ai.examples.demo",
    "talktrace_ai.config.config_manager",
    "talktrace_ai.transcript_analyzer",
    "talktrace_ai.utils",
]

# Also collect all talktrace_ai submodules automatically
all_hiddenimports += collect_submodules("talktrace_ai")

# ---------------------------------------------------------------------------
# 4.  Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",       # not needed, saves ~10 MB
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TalkTraceAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX causes false AV positives
    console=True,           # keep console visible for v1 debugging
    icon=None,              # TODO: add .ico in a future phase
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TalkTraceAI",
)
