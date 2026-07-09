"""Custom provider: chat-completion call against a user-supplied endpoint.

The "custom" backend lets users wire up any OpenAI-compatible server — a
self-hosted vLLM/llama.cpp instance, an institutional gateway, an Azure
proxy — by entering its base URL and key in the Options tab. We reuse the
official ``openai`` Python SDK with that base URL (see
``llm_clients.get_custom_client``), the same pattern as Mistral / DeepSeek /
LocalMind, so streaming, error types and JSON-mode support come for free.

Because "custom" is not one fixed host, the response-cache tag embeds the
client's base URL: the same model id served by two different endpoints must
never share cache entries.

Structured-output handling mirrors the other OpenAI-compatible modules: try
strict ``json_schema`` first, fall back to ``json_object``, then
unconstrained. Self-hosted servers vary widely in what they accept — the
fallback chain plus the prompt-side JSON instruction covers all three cases.
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


# Unknown backends may cap output well below the big providers; 32k matches
# the budget the other OpenAI-compatible modules use, and servers that cap
# lower surface a clear finish_reason=length hint via extract_chat_content.
MAX_OUTPUT_TOKENS = 32000


def _cache_tag(client) -> str:
    """Cache tag including the endpoint, so two hosts never share entries."""
    return f"custom@{getattr(client, 'base_url', '')}"


def _err_payload(label, exc):
    return _err_payload_raw("CUSTOM", label, exc)


def _extract_content(chat_completion):
    return _extract_content_raw(chat_completion, "CUSTOM", MAX_OUTPUT_TOKENS)


def llm_analysis_custom(system_prompt, user_prompt, model, transcript, codebook, client):
    """Classic (non-streaming) call against the custom endpoint.

    Returns a JSON string ``{"analysis": [...]}`` or ``{"error": "..."}`` —
    same contract as the other providers. Never returns ``None``.
    """
    cache_key = _cache_key(_cache_tag(client), model, system_prompt, user_prompt, transcript, codebook)
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
    print(f"[CUSTOM DEBUG] request: model={model} enum_active={has_enum_constraints(schema)}")

    def _create(response_format=None):
        kwargs = dict(messages=messages, model=model, max_tokens=MAX_OUTPUT_TOKENS)
        if response_format is not None:
            kwargs["response_format"] = response_format
        return client.chat.completions.create(**kwargs)

    try:
        try:
            chat_completion = _create({
                "type": "json_schema",
                "json_schema": {"name": "analysis", "schema": schema, "strict": True},
            })
        except BadRequestError as e:
            print(f"[CUSTOM DEBUG] json_schema rejected ({e}); falling back to json_object.")
            try:
                chat_completion = _create({"type": "json_object"})
            except BadRequestError as e2:
                print(f"[CUSTOM DEBUG] json_object also rejected ({e2}); going unconstrained.")
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
        return _err_payload("Model not found on the custom endpoint", e)
    except RateLimitError as e:
        return _err_payload("Rate limit / insufficient credits", e)
    except InternalServerError as e:
        return _err_payload("Custom endpoint server error", e)
    except BadRequestError as e:
        return _err_payload("Bad request", e)
    except APIError as e:
        return _err_payload("API error", e)
    except Exception as e:
        return _err_payload("Unexpected error", e)


def llm_analysis_custom_stream(
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

    Uses the JSONL output contract (one JSON object per line, no wrapper) —
    same as the other streaming providers. OpenAI-compatible servers support
    streaming across the board; ones that don't surface an APIError that the
    handler shows verbatim.
    """
    cache_key = _cache_key(_cache_tag(client), model, system_prompt, user_prompt, transcript, codebook)
    cached = _cache_get(cache_key)
    if cached is not None:
        print(f"[CUSTOM STREAM] cache=HIT key={cache_key[:8]} — replaying")
        yield from _replay_cached(cached)
        return

    print(f"[CUSTOM STREAM] request: model={model} stream=True")

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
        for chunk in stream:
            if _cancel_token is not None and _cancel_token.is_cancelled():
                print(f"[CUSTOM STREAM] cancelled by user after {emitted_count} items")
                yield {"type": "cancelled", "items_so_far": emitted_count}
                return
            try:
                choice = chunk.choices[0]
            except (IndexError, AttributeError):
                continue
            delta = getattr(choice, "delta", None)
            text = getattr(delta, "content", None) if delta is not None else None
            if not text:
                continue
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
            print(f"[CUSTOM STREAM] 0 items — raw text preview ({len(full_text)} chars): {preview}")
            if not full_text:
                yield {"type": "error", "message":
                    "The custom endpoint returned an empty stream. Check the base URL, "
                    "model slug and credentials."}
            else:
                yield {"type": "error", "message":
                    f"Model did not produce JSONL output ({len(full_text)} chars of non-JSONL text). "
                    "Try a different model on this endpoint (instruct models honour JSONL most reliably)."}
            return

        raw_json = json.dumps({"analysis": items_for_cache}, ensure_ascii=False)
        _cache_put(cache_key, raw_json)
        yield {"type": "done", "raw_json": raw_json, "stop_reason": "completed"}

    except AuthenticationError as e:
        yield {"type": "error", "message": f"Authentication failed: {e}"}
    except PermissionDeniedError as e:
        yield {"type": "error", "message": f"Permission denied: {e}"}
    except NotFoundError as e:
        yield {"type": "error", "message": f"Model not found on the custom endpoint: {e}"}
    except RateLimitError as e:
        yield {"type": "error", "message": f"Rate limit / insufficient credits: {e}"}
    except InternalServerError as e:
        yield {"type": "error", "message": f"Custom endpoint server error: {e}"}
    except BadRequestError as e:
        yield {"type": "error", "message": f"Bad request: {e}"}
    except APIError as e:
        yield {"type": "error", "message": f"API error: {e}"}
    except Exception as e:
        print(f"[CUSTOM STREAM ERROR] unexpected: {e!r}")
        yield {"type": "error", "message": f"Unexpected error: {e}"}
