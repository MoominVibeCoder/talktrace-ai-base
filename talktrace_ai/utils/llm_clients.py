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


def fetch_localmind_models(api_key):
    """Return the model ids LocalMind exposes via ``GET /v1/models``.

    LocalMind's model line-up is a live gateway catalogue — the exact slugs
    are not published, so instead of hard-coding a guess we let the user
    pull the authoritative list from the endpoint they authenticate against.
    Used by the "load LocalMind models" button in the Options tab.

    Returns a sorted list of model-id strings. Raises the underlying SDK
    exception (AuthenticationError, APIConnectionError, …) on failure so the
    caller can surface a specific message.
    """
    client = get_localmind_client(api_key)
    page = client.models.list()
    ids = [m.id for m in getattr(page, "data", []) if getattr(m, "id", None)]
    return sorted(set(ids))


