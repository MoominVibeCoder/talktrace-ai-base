"""DeepSeek provider: chat-completion call via OpenAI-compatible REST API.

DeepSeek (https://api-docs.deepseek.com/) exposes its chat-completion API
as an OpenAI-compatible endpoint at ``https://api.deepseek.com/v1``. Like
Mistral and OpenRouter, we reuse the official ``openai`` Python SDK with a
custom ``base_url``.

Why DeepSeek made the Big-4 cut:
  * Frontier-class quality at fraction-of-OpenAI cost (deepseek-chat V3:
    ~ $0.27/$1.10 per 1M; deepseek-reasoner R1: ~ $0.55/$2.19). The
    cost compression is the differentiator that lets a small academic
    project run multi-coder studies that would otherwise be infeasible.
  * Mature reasoning model (deepseek-reasoner / R1) — useful as a third
    coder paradigm next to GPT and Claude for the inter-coder reliability
    studies the dissertation rests on.

Reasoning-model wrinkle: ``deepseek-reasoner`` returns its chain-of-thought
in a separate ``reasoning_content`` field on the message; the actual
response sits in ``content``. The streaming delta carries
``reasoning_content`` chunks before any content chunks. We deliberately
**skip** ``reasoning_content`` deltas in the stream loop — the JSONL
parser would choke on free-form thinking text — and only buffer the
``content`` deltas. The non-streaming path uses ``message.content``
directly, which is already CoT-stripped.

Structured-output handling:
  * ``deepseek-chat`` supports ``response_format={"type": "json_object"}``
    reliably; strict ``json_schema`` is not stable as of late 2025 and
    typically downgraded silently. We try json_schema first anyway (in
    case it lands), fall back to json_object, then unconstrained.
  * ``deepseek-reasoner`` does **not** support response_format at all —
    the API rejects the parameter. We catch that and re-issue without it.
"""
import json

from openai import (
    BadRequestError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    InternalServerError,
    APIError,
)

from ..llm_cache import _cache_key, _cache_get, _cache_put
from ._json import _format_codebook
from ._prompts import jsonl_override
from ._schema import build_analysis_schema, has_enum_constraints
from ._shared import (
    replay_cached as _replay_cached,
    err_payload as _err_payload_raw,
    extract_chat_content as _extract_content_raw,
)
from ._stream_parse import parse_jsonl_line, normalize_item


# DeepSeek caps output at 8k by default and 64k with the
# ``--enable-thinking`` toggle on the reasoner. 32k is a safe middle that
# avoids the silent-truncation case on long lessons without burning the
# full budget on every coding pass.
MAX_OUTPUT_TOKENS = 32000


def _is_reasoner(model: str) -> bool:
    """Reasoner needs a different request shape (no response_format)."""
    return "reasoner" in (model or "").lower()


def _err_payload(label, exc):
    return _err_payload_raw("DEEPSEEK", label, exc)


def _extract_content(chat_completion):
    return _extract_content_raw(chat_completion, "DEEPSEEK", MAX_OUTPUT_TOKENS)


def llm_analysis_deepseek(system_prompt, user_prompt, model, transcript, codebook, client):
    """Classic (non-streaming) DeepSeek call.

    Returns a JSON string ``{"analysis": [...]}`` or ``{"error": "..."}`` —
    same contract as the other providers. Never returns ``None``.
    """
    cache_key = _cache_key("deepseek", model, system_prompt, user_prompt, transcript, codebook)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": user_prompt.replace("{transcript}", str(transcript)).replace("{codebook}", _format_codebook(codebook)),
        },
    ]

    schema = build_analysis_schema(codebook, transcript)
    print(f"[DEEPSEEK DEBUG] request: model={model} enum_active={has_enum_constraints(schema)}")

    def _create(response_format=None):
        kwargs = dict(messages=messages, model=model, max_tokens=MAX_OUTPUT_TOKENS)
        if response_format is not None:
            kwargs["response_format"] = response_format
        return client.chat.completions.create(**kwargs)

    try:
        if _is_reasoner(model):
            # reasoner rejects response_format outright; use prompt-driven JSON.
            chat_completion = _create(None)
        else:
            try:
                chat_completion = _create({
                    "type": "json_schema",
                    "json_schema": {"name": "analysis", "schema": schema, "strict": True},
                })
            except BadRequestError as e:
                print(f"[DEEPSEEK DEBUG] json_schema rejected ({e}); falling back to json_object.")
                try:
                    chat_completion = _create({"type": "json_object"})
                except BadRequestError as e2:
                    print(f"[DEEPSEEK DEBUG] json_object also rejected ({e2}); going unconstrained.")
                    chat_completion = _create(None)

        analysis_json_string = _extract_content(chat_completion)
        try:
            parsed = json.loads(analysis_json_string)
            if not (isinstance(parsed, dict) and "error" in parsed):
                _cache_put(cache_key, analysis_json_string)
        except (json.JSONDecodeError, ValueError):
            _cache_put(cache_key, analysis_json_string)
        return analysis_json_string

    except AuthenticationError as e:
        return _err_payload("Authentication failed", e)
    except PermissionDeniedError as e:
        return _err_payload("Permission denied", e)
    except NotFoundError as e:
        return _err_payload("Model not found on DeepSeek", e)
    except RateLimitError as e:
        return _err_payload("Rate limit / insufficient balance", e)
    except InternalServerError as e:
        return _err_payload("DeepSeek server error", e)
    except BadRequestError as e:
        return _err_payload("Bad request", e)
    except APIError as e:
        return _err_payload("API error", e)
    except Exception as e:
        return _err_payload("Unexpected error", e)


def llm_analysis_deepseek_stream(
    system_prompt,
    user_prompt,
    model,
    transcript,
    codebook,
    client,
    language="de",
    _cancel_token=None,
):
    """Sync generator yielding {"type": "item"|"done"|"error"|"cancelled", ...} events.

    Reasoner caveat: when streaming, the model first emits a series of
    ``reasoning_content`` deltas (the chain-of-thought) followed by
    ``content`` deltas (the actual answer). We discard the reasoning
    deltas — they are free-form prose that would corrupt the JSONL
    line buffer. The user sees streaming start later for the reasoner
    than for deepseek-chat, but the items still appear progressively
    once the model transitions out of CoT.
    """
    cache_key = _cache_key("deepseek", model, system_prompt, user_prompt, transcript, codebook)
    cached = _cache_get(cache_key)
    if cached is not None:
        print(f"[DEEPSEEK STREAM] cache=HIT key={cache_key[:8]} — replaying")
        yield from _replay_cached(cached)
        return

    is_reasoner = _is_reasoner(model)
    print(f"[DEEPSEEK STREAM] request: model={model} stream=True reasoner={is_reasoner}")

    try:
        override = jsonl_override(language)
        rendered_user = (
            user_prompt.replace("{transcript}", str(transcript))
                       .replace("{codebook}", _format_codebook(codebook))
        )
        messages = [
            {"role": "system", "content": system_prompt + override},
            {"role": "user", "content": rendered_user + override},
        ]
        stream = client.chat.completions.create(
            messages=messages,
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            stream=True,
        )

        line_buffer = ""
        full_text = ""
        items_for_cache = []
        emitted_count = 0
        seen_content = False  # only relevant for the reasoner — diagnostic
        for chunk in stream:
            if _cancel_token is not None and _cancel_token.is_cancelled():
                print(f"[DEEPSEEK STREAM] cancelled by user after {emitted_count} items")
                yield {"type": "cancelled", "items_so_far": emitted_count}
                return
            try:
                choice = chunk.choices[0]
            except (IndexError, AttributeError):
                continue
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            # Reasoner: skip CoT, only buffer content. Non-reasoner:
            # ``reasoning_content`` is always None, so the check is harmless.
            text = getattr(delta, "content", None)
            if not text:
                continue
            seen_content = True
            full_text += text
            line_buffer += text
            while "\n" in line_buffer:
                line, line_buffer = line_buffer.split("\n", 1)
                item = parse_jsonl_line(line)
                if item is None:
                    continue
                emitted_count += 1
                if not item.get("#"):
                    item["#"] = emitted_count
                items_for_cache.append(item)
                yield {"type": "item", "data": item}

        if line_buffer.strip():
            item = parse_jsonl_line(line_buffer)
            if item is not None:
                emitted_count += 1
                if not item.get("#"):
                    item["#"] = emitted_count
                items_for_cache.append(item)
                yield {"type": "item", "data": item}

        if emitted_count == 0:
            preview = full_text[:400].replace("\n", " ⏎ ") if full_text else "<empty>"
            print(f"[DEEPSEEK STREAM] 0 items — raw text preview ({len(full_text)} chars): {preview}")
            if not full_text:
                if is_reasoner and not seen_content:
                    yield {"type": "error", "message":
                        "Reasoner emitted only reasoning content, no final answer. "
                        "The transcript may have exhausted the reasoning budget — try a shorter input."}
                else:
                    yield {"type": "error", "message":
                        "DeepSeek returned an empty stream. Check model slug and account balance."}
            else:
                yield {"type": "error", "message":
                    f"Model did not produce JSONL output ({len(full_text)} chars of non-JSONL text). "
                    "Try deepseek-chat (the reasoner sometimes ignores the JSONL instruction)."}
            return

        raw_json = json.dumps({"analysis": items_for_cache}, ensure_ascii=False)
        _cache_put(cache_key, raw_json)
        yield {"type": "done", "raw_json": raw_json, "stop_reason": "completed"}

    except AuthenticationError as e:
        yield {"type": "error", "message": f"Authentication failed: {e}"}
    except PermissionDeniedError as e:
        yield {"type": "error", "message": f"Permission denied: {e}"}
    except NotFoundError as e:
        yield {"type": "error", "message": f"Model not found on DeepSeek: {e}"}
    except RateLimitError as e:
        yield {"type": "error", "message": f"Rate limit / insufficient balance: {e}"}
    except InternalServerError as e:
        yield {"type": "error", "message": f"DeepSeek server error: {e}"}
    except BadRequestError as e:
        yield {"type": "error", "message": f"Bad request: {e}"}
    except APIError as e:
        yield {"type": "error", "message": f"API error: {e}"}
    except Exception as e:
        print(f"[DEEPSEEK STREAM ERROR] unexpected: {e!r}")
        yield {"type": "error", "message": f"Unexpected error: {e}"}


