"""Freeform (plain-text) chat completion for the Feedback tab.

Unlike ``llm_analysis/_core`` (structured JSON coding with schema/tool
machinery, codebook + transcript injection and a response cache), this is a
single, cache-free chat call that returns prose. It reuses the same per-provider
SDK clients as the coding pipeline but speaks each provider's *plain* chat
surface:

  * OpenAI    -> Responses API (``client.responses.create`` / ``output_text``)
  * Anthropic -> Messages API (``client.messages.create``, text content blocks)
  * Mistral / DeepSeek / LocalMind / custom -> OpenAI-compatible ``chat.completions``

We deliberately do NOT use ``_shared.extract_chat_content`` here: that helper
returns a JSON ``{"error": ...}`` blob (never ``None``) on empty/refusal/length,
which would then be rendered verbatim as "feedback". Instead we read the content
directly and raise a ``RuntimeError`` with a stable marker the handler maps to a
localized notification.
"""
from __future__ import annotations

from ..llm_clients import (
    get_openai_client, get_anthropic_client,
    get_mistral_client, get_deepseek_client, get_localmind_client,
    get_custom_client,
)
from ...config.config_manager import KNOWN_PROVIDERS, is_custom_provider

# Providers that speak the OpenAI-compatible chat.completions surface (the
# OpenAI SDK pointed at a custom base_url). OpenAI proper uses the Responses
# API instead, Anthropic its own Messages API — both handled separately.
_OPENAI_CHAT_FACTORIES = {
    "mistral": get_mistral_client,
    "deepseek": get_deepseek_client,
    "localmind": get_localmind_client,
}


def chat_completion(provider, model, system_prompt, user_prompt, api_key,
                    *, max_tokens=4000, base_url=None):
    """Return the model's plain-text answer to (system_prompt, user_prompt).

    ``base_url`` is only consumed by the custom provider (the user-supplied
    OpenAI-compatible endpoint). Raises ``ValueError`` for an unknown
    provider, ``RuntimeError('feedback_empty')`` when the model returns no
    text, and ``RuntimeError('feedback_failed: ...')`` on any SDK/network
    error.
    """
    provider = (provider or "").lower()
    if provider not in KNOWN_PROVIDERS and not is_custom_provider(provider):
        raise ValueError(f"unknown provider: {provider!r}")
    if not api_key:
        raise RuntimeError("feedback_failed: missing API key")
    if not model:
        raise RuntimeError("feedback_failed: no model selected")
    if is_custom_provider(provider) and not base_url:
        raise RuntimeError("feedback_failed: custom provider has no base URL configured")

    try:
        if provider == "anthropic":
            client = get_anthropic_client(api_key)
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(
                getattr(b, "text", "") for b in (resp.content or [])
                if getattr(b, "type", "") == "text"
            )
        elif provider == "openai":
            client = get_openai_client(api_key)
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_output_tokens=max_tokens,
            )
            text = resp.output_text
        else:
            if is_custom_provider(provider):
                client = get_custom_client(api_key, base_url)
            else:
                client = _OPENAI_CHAT_FACTORIES[provider](api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface any provider/network error
        raise RuntimeError(f"feedback_failed: {exc}") from exc

    if not text or not str(text).strip():
        raise RuntimeError("feedback_empty")
    return str(text).strip()
