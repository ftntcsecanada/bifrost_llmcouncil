"""LLM-wiki / SKILL.md context store.

Uploaded text files live in WIKI_DIR and are injected (all of them, capped)
into every council stage prompt as reference context.
"""

import os
from typing import Dict, List

from .config import WIKI_DIR, WIKI_MAX_CHARS

ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt"}
SKILL_FILE = "SKILL.md"


def _path(name: str) -> str:
    return os.path.join(WIKI_DIR, os.path.basename(name))


def save_file(filename: str, data: bytes) -> Dict:
    """Validate and store an uploaded file. Raises ValueError if invalid."""
    name = os.path.basename(filename or "")
    if not name or os.path.splitext(name)[1].lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .md, .markdown and .txt files are supported")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 text")
    os.makedirs(WIKI_DIR, exist_ok=True)
    with open(_path(name), "wb") as f:
        f.write(data)
    return {"name": name, "size": len(data)}


def list_files() -> List[Dict]:
    if not os.path.isdir(WIKI_DIR):
        return []
    return [
        {"name": n, "size": os.path.getsize(os.path.join(WIKI_DIR, n))}
        for n in sorted(os.listdir(WIKI_DIR))
        if os.path.splitext(n)[1].lower() in ALLOWED_EXTENSIONS
    ]


def delete_file(name: str) -> bool:
    p = _path(name)
    if os.path.isfile(p):
        os.remove(p)
        return True
    return False


def build_context(max_chars: int = None) -> str:
    """Concatenate all wiki files (SKILL.md first), truncated to max_chars."""
    max_chars = WIKI_MAX_CHARS if max_chars is None else max_chars
    files = sorted(list_files(), key=lambda f: (f["name"] != SKILL_FILE, f["name"]))
    if not files:
        return ""
    parts, used, truncated = [], 0, False
    for f in files:
        with open(_path(f["name"]), encoding="utf-8") as fh:
            text = fh.read()
        room = max_chars - used
        if room <= 0:
            truncated = True
            break
        if len(text) > room:
            text, truncated = text[:room], True
        parts.append(f"--- {f['name']} ---\n{text}")
        used += len(text)
    out = "\n\n".join(parts)
    if truncated:
        out += "\n\n[... wiki context truncated ...]"
    return out


def with_context(prompt: str) -> str:
    """Prefix a prompt with wiki context, if any is uploaded."""
    ctx = build_context()
    if not ctx:
        return prompt
    return (
        "Use the following reference material (an LLM wiki / SKILL.md) when it is "
        "relevant to the question. Follow any instructions in SKILL.md.\n\n"
        f"<wiki>\n{ctx}\n</wiki>\n\n{prompt}"
    )
