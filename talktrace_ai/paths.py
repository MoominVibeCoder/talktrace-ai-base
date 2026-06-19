import sys
from pathlib import Path

_WELCOME_FLAG_FILE = Path(__file__).parent / "config" / ".welcome_shown"
_DATAPROTECTION_FLAG_FILE = Path(__file__).parent / "config" / ".dataprotection_acknowledged"


def _welcome_shown():
    return _WELCOME_FLAG_FILE.exists()


def _mark_welcome_shown():
    try:
        _WELCOME_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _WELCOME_FLAG_FILE.touch()
    except OSError:
        pass


def _dataprotection_acknowledged():
    return _DATAPROTECTION_FLAG_FILE.exists()


def _dataprotection_kind():
    """Stored data kind: 'consent' | 'fictive' (acknowledged with a recorded
    choice), '' (acknowledged by a legacy flag file with no choice stored), or
    None (not acknowledged). Used to seed AppState.data_consent_given so a
    returning user is not re-prompted."""
    if not _DATAPROTECTION_FLAG_FILE.exists():
        return None
    try:
        content = _DATAPROTECTION_FLAG_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        content = ""
    return content if content in ("consent", "fictive") else ""


def _mark_dataprotection_acknowledged(kind: str = ""):
    """Persist the acknowledgment. ``kind`` ('consent'/'fictive') is stored as
    the file content so the choice survives a restart; an empty string keeps
    the historical touch-only behaviour."""
    try:
        _DATAPROTECTION_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DATAPROTECTION_FLAG_FILE.write_text(kind or "", encoding="utf-8")
    except OSError:
        pass


def _clear_dataprotection_acknowledged():
    """Remove the flag so the gate stays closed until the user re-confirms.
    Used by the Start-tab "change" action: closing the app after "change"
    but before re-confirming must NOT silently restore the old choice."""
    try:
        _DATAPROTECTION_FLAG_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def resource_path(relative_path: str) -> Path:
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path
