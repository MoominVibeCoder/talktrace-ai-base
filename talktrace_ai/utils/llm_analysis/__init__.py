"""Per-provider LLM analysis pipelines.

Public entry points (one per provider). Each takes a system prompt, user
prompt, model id, transcript text, codebook, plus an SDK client and returns
a JSON string of coded impulses.

To add a new provider:
    1. Create ``utils/llm_analysis/<name>.py`` with a ``llm_analysis_<name>``
       function. Use one of the existing modules as a template.
    2. Add the import + re-export below.
    3. Wire it into the ConfigManager + ``handlers/server_body.py`` provider
       routing logic.

base v1: OpenAI, Anthropic, Mistral, DeepSeek + LocalMind (EU-hosted gateway,
the default provider).
"""
from .openai import llm_analysis_openai, llm_analysis_openai_stream
from .anthropic import llm_analysis_anthropic, llm_analysis_anthropic_stream
from .mistral import llm_analysis_mistral, llm_analysis_mistral_stream
from .deepseek import llm_analysis_deepseek, llm_analysis_deepseek_stream
from .localmind import llm_analysis_localmind, llm_analysis_localmind_stream
from ._stream_bridge import async_stream

__all__ = [
    "llm_analysis_openai",
    "llm_analysis_anthropic",
    "llm_analysis_mistral",
    "llm_analysis_deepseek",
    "llm_analysis_localmind",
    "llm_analysis_openai_stream",
    "llm_analysis_anthropic_stream",
    "llm_analysis_mistral_stream",
    "llm_analysis_deepseek_stream",
    "llm_analysis_localmind_stream",
    "async_stream",
]
