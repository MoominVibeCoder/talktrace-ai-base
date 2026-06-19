from shiny import ui

from ..paths import resource_path
from ..theme import load_theme_css


def _load_js(name: str) -> str:
    return resource_path(f"static/{name}").read_text(encoding="utf-8")


def head_content():
    return ui.head_content(
        # Empty inline favicon so the browser stops requesting /favicon.ico.
        ui.tags.link(rel="icon", href="data:,"),
        ui.tags.style(load_theme_css()),
        ui.tags.script(_load_js("theme_sync.js")),
        ui.tags.script(_load_js("tooltip_quickstart.js")),
        ui.tags.script(_load_js("noscribe_trim.js")),
    )
