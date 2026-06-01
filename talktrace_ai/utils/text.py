"""talktrace_ai.utils.text"""
import html as _html


def html_escape(s) -> str:
    """Escape HTML special characters.  None → empty string."""
    if s is None:
        return ""
    return _html.escape(str(s))
