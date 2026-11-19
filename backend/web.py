"""Optional web-search fallback for questions the LLM wiki doesn't cover.

Flow (per question, only when the UI toggle is on):
  1. A small model checks whether the wiki context answers the question.
  2. If not, DuckDuckGo (ddgs, no API key) is searched once.
  3. Results are stored in a ContextVar and added to the prompt of every model
     listed in WEB_SEARCH_MODELS (see `apply_web`, called from bifrost.query_model).
"""

import asyncio
from contextvars import ContextVar
from typing import Dict, List

from . import wiki
from .bifrost import query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL, TITLE_MODEL, WEB_SEARCH_MODELS

web_context: ContextVar[str] = ContextVar("web_context", default="")


def _ddg_text(query: str, n: int) -> List[Dict]:
    from ddgs import DDGS

    return list(DDGS().text(query, max_results=n))


async def search(query: str, n: int = 5) -> List[Dict]:
    """Search the web; never raises (returns [] on any failure)."""
    try:
        return await asyncio.to_thread(_ddg_text, query[:300], n)
    except Exception as e:
        print(f"Web search failed: {e}")
        return []


def format_context(results: List[Dict]) -> str:
    lines = [
        f"[{i}] {r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
        for i, r in enumerate(results, 1)
    ]
    return (
        "The wiki does not cover this question. Web search results are below; "
        "use them if relevant, cite the source URLs you rely on, and say when "
        "you are unsure.\n<web>\n" + "\n\n".join(lines) + "\n</web>"
    )


def apply_web(model: str, messages: List[Dict]) -> List[Dict]:
    """Prepend web context to the last user message for models allowed to use it."""
    ctx = web_context.get()
    if not ctx or model not in WEB_SEARCH_MODELS:
        return messages
    out = [dict(m) for m in messages]
    for m in reversed(out):
        if m.get("role") == "user":
            m["content"] = f"{ctx}\n\n{m['content']}"
            break
    return out


async def wiki_covers(query: str) -> bool:
    """Ask a small model whether the wiki context answers `query` (False if no wiki/failure)."""
    ctx = wiki.build_context(query=query)
    if not ctx:
        return False
    prompt = (
        f"<wiki>\n{ctx}\n</wiki>\n\nQuestion: {query}\n\n"
        "Does the wiki above contain the information needed to answer this question? "
        "Reply with exactly one word: YES or NO."
    )
    res = await query_model(TITLE_MODEL, [{"role": "user", "content": prompt}], timeout=60.0)
    if not res or not res.get("content"):
        return False
    return res["content"].strip().upper().startswith("YES")


async def prepare(query: str, enabled: bool) -> List[Dict]:
    """Run the fallback if enabled; sets the context var and returns sources [{title,url}]."""
    web_context.set("")
    if not enabled or await wiki_covers(query):
        return []
    results = await search(query)
    if not results:
        return []
    web_context.set(format_context(results))
    return [{"title": r.get("title", ""), "url": r.get("href", "")} for r in results]
