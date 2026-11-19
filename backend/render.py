"""Render a stored conversation as a standalone HTML page (3-stage council view)."""

from html import escape
from typing import Any, Dict, List

from .council import calculate_aggregate_rankings

CSS = """
:root{--bg:#f5f5f5;--surface:#fff;--ink:#333;--ink-2:#666;--line:#e0e0e0;--accent:#4a90e2;
--accent-soft:#e8f0fe;--final-bg:#f0fff0;--final-line:#c8e6c8;
--f:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#161a1f;--surface:#1e242b;
--ink:#e8eaed;--ink-2:#a0a7b0;--line:#333b44;--accent:#6aa9ee;--accent-soft:#1c2f4a;
--final-bg:#17291c;--final-line:#2f5a38}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--f);padding:24px 16px}
main{max-width:920px;margin:0 auto}
h1{font-size:1.4rem;margin:0 0 4px}.meta{color:var(--ink-2);font-size:.85rem;margin-bottom:24px}
.turn{margin-bottom:36px}
.q{background:var(--accent-soft);border-left:4px solid var(--accent);padding:12px 16px;border-radius:6px;white-space:pre-wrap}
.stage{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin-top:16px;padding:4px 16px 12px}
.stage>h2{font-size:1rem;margin:12px 0 8px}.stage>h2 small{color:var(--ink-2);font-weight:400}
.stage.final{background:var(--final-bg);border-color:var(--final-line)}
details{border-top:1px solid var(--line);padding:8px 0}details:first-of-type{border-top:0}
summary{cursor:pointer;font-weight:600;font-family:ui-monospace,monospace;font-size:.9rem}
.md{padding:8px 4px;overflow-wrap:anywhere}.md pre{overflow-x:auto;background:var(--bg);padding:10px;border-radius:6px}
.md table{border-collapse:collapse}.md td,.md th{border:1px solid var(--line);padding:4px 8px}
.raw{white-space:pre-wrap}
.extract{font-size:.85rem;color:var(--ink-2);border-top:1px dashed var(--line);padding-top:6px}
table.agg{border-collapse:collapse;margin:8px 0;width:100%}
table.agg td,table.agg th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
"""

JS = """
(function(){
 if(!window.marked||!window.DOMPurify)return;
 document.querySelectorAll('.md').forEach(function(el){
  el.innerHTML=DOMPurify.sanitize(marked.parse(el.textContent));el.classList.remove('raw');});
})();
"""


def _md(text: str) -> str:
    # Escaped raw text; client-side marked+DOMPurify upgrade it to rendered markdown.
    return f'<div class="md raw">{escape(text or "")}</div>'


def _label_map(stage1: List[Dict[str, Any]]) -> Dict[str, str]:
    return {f"Response {chr(65 + i)}": r["model"] for i, r in enumerate(stage1)}


def _stage1(stage1) -> str:
    items = "".join(
        f'<details{" open" if i == 0 else ""}><summary>{escape(r["model"])}</summary>{_md(r["response"])}</details>'
        for i, r in enumerate(stage1)
    )
    return f'<section class="stage"><h2>Stage 1 <small>individual responses</small></h2>{items}</section>'


def _stage2(stage1, stage2) -> str:
    l2m = _label_map(stage1)
    evals = ""
    for r in stage2:
        parsed = r.get("parsed_ranking") or []
        extracted = " &rarr; ".join(
            f"{escape(p)} ({escape(l2m.get(p, '?'))})" for p in parsed
        )
        evals += (
            f'<details><summary>{escape(r["model"])}</summary>{_md(r["ranking"])}'
            f'<div class="extract"><b>Extracted ranking:</b> {extracted or "none parsed"}</div></details>'
        )
    agg = calculate_aggregate_rankings(stage2, l2m)
    rows = "".join(
        f'<tr><td>{i}</td><td>{escape(a["model"])}</td><td>{a["average_rank"]}</td><td>{a["rankings_count"]}</td></tr>'
        for i, a in enumerate(agg, 1)
    )
    table = (
        '<h3>Aggregate rankings</h3><table class="agg"><tr><th>#</th><th>Model</th>'
        f"<th>Avg position</th><th>Votes</th></tr>{rows}</table>"
        if agg
        else ""
    )
    note = ("<p class=\"meta\">Models saw anonymous labels (Response A, B, …); "
            "model names are shown here for readability only.</p>")
    return (f'<section class="stage"><h2>Stage 2 <small>anonymized peer review</small></h2>'
            f"{note}{evals}{table}</section>")


def _stage3(s3) -> str:
    return (f'<section class="stage final"><h2>Stage 3 <small>chairman: {escape(s3["model"])}</small></h2>'
            f'{_md(s3["response"])}</section>')


def render_conversation_html(conv: Dict[str, Any]) -> str:
    turns = ""
    for m in conv.get("messages", []):
        if m.get("role") == "user":
            turns += f'<div class="turn"><div class="q">{escape(m["content"])}</div>'
        else:
            s1, s2, s3 = m.get("stage1") or [], m.get("stage2") or [], m.get("stage3")
            turns += (_stage1(s1) if s1 else "") + (_stage2(s1, s2) if s2 else "")
            turns += (_stage3(s3) if s3 else "") + "</div>"
    title = escape(conv.get("title") or "Council")
    created = escape(str(conv.get("created_at", "")))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{CSS}</style></head><body><main>"
        f"<h1>{title}</h1><div class=\"meta\">FortiAICouncil &middot; {created}</div>{turns}</main>"
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.1.6/purify.min.js"></script>'
        f"<script>{JS}</script></body></html>"
    )
