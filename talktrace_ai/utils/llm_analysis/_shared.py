"""Shared helpers used by multiple LLM provider modules.

Extracted from per-provider code that was copy-pasted across openai.py,
anthropic.py, mistral.py, and deepseek.py. Zero provider-specific logic
lives here — everything is parameterised by a provider tag string where
needed (log messages only).
"""
import json

import pandas as pd

from ._stream_parse import normalize_item


# Kernspalten des Analyse-DataFrames — die internen (deutschen) Schlüssel,
# die die gesamte Pipeline durchziehen (siehe examples/demo.py Docstring).
ANALYSIS_COLUMNS = ["#", "Sprecher", "Shortcode", "Impuls"]


def analysis_items_to_df(items):
    """Build the analysis DataFrame from parsed LLM items.

    Always carries the four core columns; the optional "Konfidenz" column
    (multi-coding with confidence) is only added when at least one item has
    a confidence value — legacy output and single-coding keep the classic
    4-column shape, so older sessions and downstream consumers see no change.
    """
    cols = list(ANALYSIS_COLUMNS)
    if any(isinstance(it, dict) and it.get("Konfidenz") is not None for it in (items or [])):
        cols.append("Konfidenz")
    return pd.DataFrame(items, columns=cols)


def replay_cached(cached_json):
    """Replay a cached ``{"analysis": [...]}`` payload as a stream of events.

    Yields ``{"type": "item", ...}`` for each coded item, then a single
    ``{"type": "done", ...}``.  Used identically by every streaming provider
    on a cache hit so the UI sees the same per-item flow as a fresh API call.
    """
    try:
        obj = json.loads(cached_json)
    except (json.JSONDecodeError, ValueError):
        yield {"type": "error", "message": "Cached payload was unparseable."}
        return
    items = (
        obj.get("analysis", [])
        if isinstance(obj, dict)
        else (obj if isinstance(obj, list) else [])
    )
    for raw in items:
        norm = normalize_item(raw) if isinstance(raw, dict) else None
        if norm is not None:
            yield {"type": "item", "data": norm}
    yield {"type": "done", "raw_json": cached_json, "stop_reason": "cache_hit"}


def err_payload(provider_tag, label, exc):
    """Build a JSON error string and log it.  Used by the non-streaming paths
    of Mistral and DeepSeek for consistent error surfacing.
    """
    msg = str(exc) if exc is not None else "(no message)"
    print(f"[{provider_tag} ERROR] {label}: {msg}")
    return json.dumps({"error": f"{label}: {msg}"})


def extract_chat_content(chat_completion, provider_tag, max_output_tokens):
    """Pull the response text out of an OpenAI-compatible chat-completion choice.

    Works for any provider that returns OpenAI-shaped completions (Mistral,
    DeepSeek, OpenRouter).  Handles ``content=None`` with either a ``parsed``
    field, a refusal, or a ``finish_reason=length`` burnout.  Never returns
    ``None``.

    *provider_tag* is only used in log/error messages (e.g. ``"MISTRAL"``).
    *max_output_tokens* is shown in the length-burnout hint.
    """
    try:
        choice = chat_completion.choices[0]
    except (IndexError, AttributeError):
        return json.dumps({"error": f"{provider_tag} returned no choices."})

    msg = getattr(choice, "message", None)
    content = getattr(msg, "content", None) if msg is not None else None
    if content:
        return content

    parsed = getattr(msg, "parsed", None) if msg is not None else None
    if parsed is not None:
        try:
            return json.dumps(parsed, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            print(f"[{provider_tag} WARN] could not re-encode .parsed: {e}")

    refusal = getattr(msg, "refusal", None) if msg is not None else None
    if refusal:
        print(f"[{provider_tag} WARN] model refused: {refusal}")
        return json.dumps({"error": f"Model refused: {refusal}"})

    finish = getattr(choice, "finish_reason", None)
    print(f"[{provider_tag} WARN] empty content (finish_reason={finish})")
    if finish == "length":
        return json.dumps({"error": (
            f"Token-Budget aufgebraucht (max_tokens={max_output_tokens}, "
            "finish_reason=length). Das Modell hat das Output-Budget "
            "verbraucht. Versuche ein anderes Modell oder ein "
            "kuerzeres Transkript."
        )})
    return json.dumps({
        "error": f"Model returned empty content (finish_reason={finish})."
    })
