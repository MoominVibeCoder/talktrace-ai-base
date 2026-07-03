"""LocalMind provider: chat-completion call via OpenAI-compatible gateway.

LocalMind (https://www.localmind.ai/) exposes an OpenAI-compatible inference
gateway at ``https://api.lminference.eu/v1``. We reuse the official
``openai`` Python SDK with a custom ``base_url`` — the same trick used for
Mistral and DeepSeek — which gives us streaming, error types, and JSON-mode
support for free without pulling in a second SDK.

Why LocalMind is the default provider:
  * EU-hosted (Austria) — the gateway keeps classroom transcripts inside the
    EU, which is the natural GDPR-conformant cloud path for school
    deployments that cannot route data to the US or China. This is the
    single most important property for TalkTrace's use case, so LocalMind is
    seeded as ``current_api`` in the default config.
  * Broad catalogue — a single key fronts the gateway's own ``localmind-*``
    models plus Llama / Mistral / Qwen / Gemma / DeepSeek / GPT-OSS. The
    exact slugs are a live catalogue fetched via ``GET /v1/models`` (see
    ``llm_clients.fetch_localmind_models`` and the Options-tab load button),
    not hard-coded here.

Structured-output handling mirrors the Mistral module: try strict
``json_schema`` first, fall back to ``json_object`` (widely supported across
the gateway's model families), then unconstrained. The prompt itself
instructs JSON output, so even the unconstrained path usually yields
parseable text. Because the catalogue includes reasoning models (DeepSeek
R1, Magistral, o-series) the gateway may return them behind a normal
``content`` field; we rely on the same ``\n``-delimited JSONL streaming
contract as the other providers.
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


# The gateway fronts many model families with different output caps; 32k is
# the same safe middle the Mistral/DeepSeek modules use — enough headroom for
# a long coding pass without over-allocating the budget on every call.
MAX_OUTPUT_TOKENS = 32000


def _err_payload(label, exc):
    return _err_payload_raw("LOCALMIND", label, exc)


def _extract_content(chat_completion):
    return _extract_content_raw(chat_completion, "LOCALMIND", MAX_OUTPUT_TOKENS)


def llm_analysis_localmind(system_prompt, user_prompt, model, transcript, codebook, client):
    """Classic (non-streaming) LocalMind call.

    Returns a JSON string ``{"analysis": [...]}`` or ``{"error": "..."}`` —
    same contract as the other providers. Never returns ``None``.
    """
    cache_key = _cache_key("localmind", model, system_prompt, user_prompt, transcript, codebook)
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
    print(f"[LOCALMIND DEBUG] request: model={model} enum_active={has_enum_constraints(schema)}")

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
            print(f"[LOCALMIND DEBUG] json_schema rejected ({e}); falling back to json_object.")
            try:
                chat_completion = _create({"type": "json_object"})
            except BadRequestError as e2:
                print(f"[LOCALMIND DEBUG] json_object also rejected ({e2}); going unconstrained.")
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
        return _err_payload("Model not found on LocalMind", e)
    except RateLimitError as e:
        return _err_payload("Rate limit / insufficient credits", e)
    except InternalServerError as e:
        return _err_payload("LocalMind server error", e)
    except BadRequestError as e:
        return _err_payload("Bad request", e)
    except APIError as e:
        return _err_payload("API error", e)
    except Exception as e:
        return _err_payload("Unexpected error", e)


def llm_analysis_localmind_stream(
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
    same as the other streaming providers. LocalMind's gateway honours
    streaming across its model line-up.
    """
    cache_key = _cache_key("localmind", model, system_prompt, user_prompt, transcript, codebook)
    cached = _cache_get(cache_key)
    if cached is not None:
        print(f"[LOCALMIND STREAM] cache=HIT key={cache_key[:8]} — replaying")
        yield from _replay_cached(cached)
        return

    print(f"[LOCALMIND STREAM] request: model={model} stream=True")

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
                print(f"[LOCALMIND STREAM] cancelled by user after {emitted_count} items")
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
            print(f"[LOCALMIND STREAM] 0 items — raw text preview ({len(full_text)} chars): {preview}")
            if not full_text:
                yield {"type": "error", "message":
                    "LocalMind returned an empty stream. Check the model slug and account credits."}
            else:
                yield {"type": "error", "message":
                    f"Model did not produce JSONL output ({len(full_text)} chars of non-JSONL text). "
                    "Try a different LocalMind model (instruct models honour JSONL most reliably)."}
            return

        raw_json = json.dumps({"analysis": items_for_cache}, ensure_ascii=False)
        _cache_put(cache_key, raw_json)
        yield {"type": "done", "raw_json": raw_json, "stop_reason": "completed"}

    except AuthenticationError as e:
        yield {"type": "error", "message": f"Authentication failed: {e}"}
    except PermissionDeniedError as e:
        yield {"type": "error", "message": f"Permission denied: {e}"}
    except NotFoundError as e:
        yield {"type": "error", "message": f"Model not found on LocalMind: {e}"}
    except RateLimitError as e:
        yield {"type": "error", "message": f"Rate limit / insufficient credits: {e}"}
    except InternalServerError as e:
        yield {"type": "error", "message": f"LocalMind server error: {e}"}
    except BadRequestError as e:
        yield {"type": "error", "message": f"Bad request: {e}"}
    except APIError as e:
        yield {"type": "error", "message": f"API error: {e}"}
    except Exception as e:
        print(f"[LOCALMIND STREAM ERROR] unexpected: {e!r}")
        yield {"type": "error", "message": f"Unexpected error: {e}"}
