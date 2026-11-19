"""Configuration for the FortiAICouncil."""

import os
from dotenv import load_dotenv

load_dotenv()

# Bifrost virtual key (sk-bf-...), read from ./.env at the project root
_raw_key = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("BIFROST_API_KEY") or ""
BIFROST_API_KEY = _raw_key.strip().lstrip("=").strip("\"' ")

# Council members - list of Bifrost model identifiers (provider/model)
COUNCIL_MODELS = [
    "vllm/qwen3-8-27b-local",
    "vllm/qwen3-8-flash-next-ant",
    "azure/glm-5.2",
    "azure/gpt-oss-120b",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "azure/gpt-5.5"

# Model for short conversation titles (smallest/fastest council model)
TITLE_MODEL = "vllm/qwen3-8-flash-next-ant"

# Models that receive web-search results when the UI toggle is on and the wiki
# does not cover the question. Models not listed stay wiki-only.
WEB_SEARCH_MODELS = list(dict.fromkeys(COUNCIL_MODELS + [CHAIRMAN_MODEL]))

# Bifrost OpenAI-compatible base URL (client appends /chat/completions)
BIFROST_API_URL = os.getenv(
    "BIFROST_API_URL", "https://bifrost.fabriclab.ca/openai/v1"
).rstrip("/")

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# LLM wiki / SKILL.md uploads, injected into every stage prompt
WIKI_DIR = "data/wiki"
WIKI_MAX_CHARS = 100_000
