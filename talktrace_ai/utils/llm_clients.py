"""talktrace_ai.utils.llm_clients"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import pandas as pd
import numpy as np
import sys
import os
import tempfile
import json
import re
import hashlib
import pickle
import keyring
import keyring.errors
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import anthropic as anthropic_sdk
import tiktoken
from ..localization.translation import TRANSLATIONS
from ..config.config_manager import ConfigManager

# Client-Cache: je API-Key wird nur ein SDK-Client instanziert.
_client_cache = {}


def get_openai_client(api_key):
    key = ("openai", api_key)
    if key not in _client_cache:
        _client_cache[key] = OpenAI(api_key=api_key)
    return _client_cache[key]


def get_anthropic_client(api_key):
    key = ("anthropic", api_key)
    if key not in _client_cache:
        _client_cache[key] = anthropic_sdk.Anthropic(api_key=api_key)
    return _client_cache[key]


def get_mistral_client(api_key):
    """OpenAI SDK pointed at Mistral's chat-completion endpoint.

    Mistral exposes an OpenAI-compatible REST API at
    ``https://api.mistral.ai/v1`` — same pattern we use for OpenRouter,
    minus the ranking headers which Mistral does not consume. Using the
    OpenAI SDK rather than the dedicated ``mistralai`` package keeps the
    provider plumbing (error types, streaming generator shape) identical
    to the other Big-4 providers, which simplifies the dispatch layer in
    ``llm_analysis._core``.
    """
    key = ("mistral", api_key)
    if key not in _client_cache:
        _client_cache[key] = OpenAI(
            api_key=api_key,
            base_url="https://api.mistral.ai/v1",
        )
    return _client_cache[key]


def get_deepseek_client(api_key):
    """OpenAI SDK pointed at DeepSeek's chat-completion endpoint.

    DeepSeek's API is OpenAI-compatible at ``https://api.deepseek.com/v1``.
    Same SDK-reuse rationale as the Mistral helper above.

    Both ``deepseek-chat`` (V3) and ``deepseek-reasoner`` (R1) are routed
    through the same client; the model id alone determines which backend
    serves the request and whether ``response_format`` is honoured (chat:
    yes; reasoner: no — see ``llm_analysis/deepseek.py`` for the dispatch
    logic).
    """
    key = ("deepseek", api_key)
    if key not in _client_cache:
        _client_cache[key] = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
        )
    return _client_cache[key]


def get_localmind_client(api_key):
    """OpenAI SDK pointed at LocalMind's EU-hosted inference gateway.

    LocalMind (https://www.localmind.ai/, Austria) runs a fully
    OpenAI-compatible gateway at ``https://api.lminference.eu/v1`` that
    fronts many open and proprietary models (its own ``localmind-*`` models
    plus Llama / Mistral / Qwen / Gemma / DeepSeek / GPT-OSS, …). Same
    SDK-reuse rationale as the Mistral / DeepSeek helpers above.

    Why LocalMind matters for TalkTrace: the gateway is hosted **inside the
    EU**, which makes it the natural GDPR-conformant cloud path for
    classroom transcripts that must not leave the EU — the reason it is the
    default provider in ``config_manager.KNOWN_PROVIDERS``.
    """
    key = ("localmind", api_key)
    if key not in _client_cache:
        _client_cache[key] = OpenAI(
            api_key=api_key,
            base_url="https://api.lminference.eu/v1",
        )
    return _client_cache[key]


def get_custom_client(api_key, base_url):
    """OpenAI SDK pointed at a user-supplied OpenAI-compatible endpoint.

    The "custom" provider lets users wire up any OpenAI-compatible server —
    a self-hosted vLLM/llama.cpp instance, an institutional gateway, an Azure
    proxy — by entering its base URL (e.g. ``https://host/v1``) and key in
    the Options tab. The cache key includes the base URL so switching
    endpoints never reuses a client bound to the old host.
    """
    key = ("custom", api_key, base_url)
    if key not in _client_cache:
        _client_cache[key] = OpenAI(api_key=api_key, base_url=base_url)
    return _client_cache[key]


def _is_chat_model(model_id: str) -> bool:
    """Filter out non-chat catalogue entries (embeddings, audio, image, …).

    ``GET /v1/models`` mixes chat LLMs with models that cannot serve the
    transcript-coding chat-completion call — embeddings (``mistral-embed-eu``,
    ``qwen-3-embedding-8b-nebius``), image generation (``gpt-image-2``,
    ``flux-2-pro-azure``, ``dall-e-3``), speech (``whisper-1``, ``tts-1``,
    ``voxtral``), moderation and OCR endpoints. None of those may appear in
    the model picker where a user could pick one and hit an opaque error.
    Conservative substring heuristic — only tokens that unambiguously mark a
    non-chat model.
    """
    low = (model_id or "").lower()
    return not any(tok in low for tok in (
        "embed", "image", "flux", "dall-e", "whisper", "tts",
        "moderation", "transcribe", "realtime", "audio", "ocr", "voxtral",
    ))


def fetch_provider_models(provider, api_key, base_url=None):
    """Return the chat-capable model ids a provider exposes via its model list.

    Works for every configured backend: the OpenAI-compatible ones (OpenAI,
    Mistral, DeepSeek, LocalMind, custom) via ``GET /v1/models`` through the
    OpenAI SDK, and Anthropic via its own ``models.list``. Model catalogues
    are living lists — this lets the user refresh the registry with one click
    instead of tracking provider release notes. Non-chat models are dropped
    (see ``_is_chat_model``). ``base_url`` is only used by the custom
    provider.

    Returns a sorted list of model-id strings. Raises the underlying SDK
    exception (AuthenticationError, APIConnectionError, …) on failure so the
    caller can surface a specific message.
    """
    factories = {
        "openai": get_openai_client,
        "anthropic": get_anthropic_client,
        "mistral": get_mistral_client,
        "deepseek": get_deepseek_client,
        "localmind": get_localmind_client,
    }
    if provider == "custom":
        if not base_url:
            raise ValueError("custom provider needs a base URL")
        client = get_custom_client(api_key, base_url)
    elif provider in factories:
        client = factories[provider](api_key)
    else:
        raise ValueError(f"unknown provider: {provider!r}")
    # Anthropic's SDK pages the same way (.data with .id entries), so one
    # extraction path covers both SDKs.
    page = client.models.list()
    ids = [m.id for m in getattr(page, "data", []) if getattr(m, "id", None)]
    return sorted(m for m in set(ids) if _is_chat_model(m))


