"""Dispatcher: ruft die Sektions-Register.

Order is irrelevant for cross-section helpers (they're published on `state`
inside each `register()` and consumed only inside reactive bodies, which
fire after all register() calls complete). UI order kept for readability.
"""
from . import onboarding, sidebar, analysis, results, options, info


def register(state):
    onboarding.register(state)
    sidebar.register(state)
    analysis.register(state)
    results.register(state)
    options.register(state)
    info.register(state)
