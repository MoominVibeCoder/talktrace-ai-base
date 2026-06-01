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


