"""LLM-wiki / SKILL.md context store.

Uploaded text files (single files or a whole wiki folder, with subfolders
preserved) live in WIKI_DIR. If the wiki fits in WIKI_MAX_CHARS it is injected
whole into every council stage prompt; otherwise SKILL.md / index.md plus the
pages most relevant to the user's question are injected.
"""

import os
import re
import shutil
from typing import Dict, List, Optional

from .config import WIKI_DIR, WIKI_MAX_CHARS

ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt"}
SKILL_FILE = "SKILL.md"
PRIORITY_FILES = {"SKILL.md", "index.md"}


def _clean(name: str) -> str:
    """Normalise to a safe relative posix path ('..', '.', empty segments dropped)."""
    parts = [p for p in re.split(r"[\\/]+", name or "") if p not in ("", ".", "..")]
    return "/".join(parts)


def _path(name: str) -> str:
    return os.path.join(WIKI_DIR, *_clean(name).split("/"))


def save_file(filename: str, data: bytes) -> Dict:
    """Validate and store an uploaded file. Raises ValueError if invalid."""
    name = _clean(filename)
    if not name or os.path.splitext(name)[1].lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .md, .markdown and .txt files are supported")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 text")
    path = _path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return {"name": name, "size": len(data)}


def list_files() -> List[Dict]:
    if not os.path.isdir(WIKI_DIR):
        return []
    out = []
    for root, _, names in os.walk(WIKI_DIR):
        for n in names:
            if os.path.splitext(n)[1].lower() not in ALLOWED_EXTENSIONS:
                continue
            full = os.path.join(root, n)
            rel = os.path.relpath(full, WIKI_DIR).replace(os.sep, "/")
            out.append({"name": rel, "size": os.path.getsize(full)})
    return sorted(out, key=lambda f: f["name"])


def delete_file(name: str) -> bool:
    p = _path(name)
    if _clean(name) and os.path.isfile(p):
        os.remove(p)
        # prune now-empty parent dirs (never WIKI_DIR itself)
        d = os.path.dirname(p)
        while os.path.abspath(d) != os.path.abspath(WIKI_DIR) and not os.listdir(d):
            os.rmdir(d)
            d = os.path.dirname(d)
        return True
    return False


def delete_folder(name: str) -> int:
    """Remove a wiki folder and everything under it. Returns files removed (0 = nothing)."""
    clean = _clean(name)
    p = _path(clean) if clean else ""
    if not clean or not os.path.isdir(p):
        return 0
    count = sum(1 for f in list_files() if f["name"].startswith(clean + "/"))
    shutil.rmtree(p)
    return count


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _is_priority(name: str) -> bool:
    return os.path.basename(name) in PRIORITY_FILES


def _score(name: str, text: str, q: set) -> int:
    """Keyword overlap; path/title matches count triple."""
    if not q:
        return 0
    head = _tokens(name + " " + text[:200])
    body = _tokens(text)
    return sum(3 for t in q if t in head) + sum(1 for t in q if t in body)


def build_context(max_chars: int = None, query: Optional[str] = None) -> str:
    """Wiki text for a prompt: everything if it fits in max_chars, otherwise
    SKILL.md / index.md first, then pages ranked by relevance to `query`."""
    max_chars = WIKI_MAX_CHARS if max_chars is None else max_chars
    files = list_files()
    if not files:
        return ""
    texts = {}
    for f in files:
        with open(_path(f["name"]), encoding="utf-8") as fh:
            texts[f["name"]] = fh.read()

    q = _tokens(query or "")
    if sum(len(t) for t in texts.values()) <= max_chars:
        order = sorted(texts, key=lambda n: (os.path.basename(n) != SKILL_FILE, n))
    else:
        order = sorted(
            texts,
            key=lambda n: (
                os.path.basename(n) != SKILL_FILE,
                not _is_priority(n),
                -_score(n, texts[n], q),
                n,
            ),
        )
        if q:  # drop pages with no relevance to the question
            order = [n for n in order if _is_priority(n) or _score(n, texts[n], q) > 0]

    parts, used, truncated = [], 0, len(order) < len(texts)
    for n in order:
        text = texts[n]
        room = max_chars - used
        if room <= 0:
            truncated = True
            break
        if len(text) > room:
            text, truncated = text[:room], True
        parts.append(f"--- {n} ---\n{text}")
        used += len(text)
    out = "\n\n".join(parts)
    if truncated:
        out += "\n\n[... wiki context truncated ...]"
    return out


def with_context(prompt: str, query: Optional[str] = None) -> str:
    """Prefix a prompt with wiki context, if any is uploaded.

    `query` (the user's question) drives page selection for large wikis;
    defaults to the prompt itself."""
    ctx = build_context(query=query if query is not None else prompt)
    if not ctx:
        return prompt
    return (
        "Use the following reference material (an LLM wiki / SKILL.md) when it is "
        "relevant to the question. Follow any instructions in SKILL.md.\n\n"
        f"<wiki>\n{ctx}\n</wiki>\n\n{prompt}"
    )
