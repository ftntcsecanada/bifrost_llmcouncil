"""Render a stored conversation as a standalone HTML report.

Layout per question: the question, the chairman's final answer first, then
collapsible detail on how the council got there (individual responses and
anonymized peer review with ranking bars).
"""

from html import escape
from typing import Any, Dict, List

from .council import calculate_aggregate_rankings

CSS = """
:root{
  --bg:#f6f7f9;--surface:#fff;--ink:#1a2230;--ink-2:#566173;--line:#e4e8ee;
  --accent:#2b6cc4;--accent-soft:#eaf1fc;--ok:#1d8a5a;--ok-soft:#eef8f2;--ok-line:#cbe8d8;
  --bar:#cfd8e6;--bar-top:#2b6cc4;
  --f:Inter,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;
  --bg:#12161c;--surface:#1b212a;--ink:#e9edf3;--ink-2:#9aa6b6;--line:#2c3541;
  --accent:#7db0f0;--accent-soft:#1a2b45;--ok:#5ccf98;--ok-soft:#14261d;--ok-line:#27493a;
  --bar:#34404f;--bar-top:#7db0f0}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 var(--f);
  -webkit-font-smoothing:antialiased;padding:32px 16px 64px}
main{max-width:860px;margin:0 auto}

header.top{margin-bottom:28px}
header.top h1{font-size:1.75rem;line-height:1.25;letter-spacing:-.01em;margin:0 0 6px}
.meta{color:var(--ink-2);font-size:.875rem}

.turn{margin-bottom:56px}
.question{background:var(--accent-soft);border-radius:12px;padding:16px 20px;
  font-size:1.05rem;font-weight:500;white-space:pre-wrap;overflow-wrap:anywhere}
.question small{display:block;color:var(--ink-2);font-weight:400;font-size:.8rem;margin-bottom:2px}

.answer{background:var(--surface);border:1px solid var(--ok-line);border-top:4px solid var(--ok);
  border-radius:12px;padding:8px 28px 24px;margin-top:20px;box-shadow:0 1px 2px rgba(20,30,50,.05)}
.answer-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;
  gap:4px 16px;padding:16px 0 4px}
.answer-head h2{font-size:1.15rem;margin:0;color:var(--ok)}
.answer-head span{color:var(--ink-2);font-size:.85rem;font-family:var(--mono)}
.answer .md{font-size:1.0625rem;line-height:1.75}

h3.section{font-size:1.05rem;margin:36px 0 4px}
p.hint{color:var(--ink-2);font-size:.9rem;margin:0 0 12px}

details.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;margin-top:10px}
details.card>summary{cursor:pointer;list-style:none;padding:12px 18px;display:flex;align-items:center;
  gap:10px;font-weight:600;font-size:.95rem}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary::before{content:"";width:7px;height:7px;border-right:2px solid var(--ink-2);
  border-bottom:2px solid var(--ink-2);transform:rotate(-45deg);transition:transform .15s}
details.card[open]>summary::before{transform:rotate(45deg)}
details.card>summary .model{font-family:var(--mono);font-size:.88rem}
details.card>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;border-radius:10px}
details.card>.body{padding:0 18px 14px;border-top:1px solid var(--line)}

.extract{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.85rem;color:var(--ink-2);
  border-top:1px dashed var(--line);padding-top:10px;margin-top:6px}
.chip{background:var(--accent-soft);color:var(--accent);border-radius:999px;padding:2px 10px;
  font-family:var(--mono);font-size:.8rem}

.rank{margin:12px 0 4px;display:grid;gap:10px}
.rank-row{display:grid;grid-template-columns:28px minmax(120px,220px) 1fr auto;gap:12px;align-items:center;font-size:.9rem}
.rank-row .pos{color:var(--ink-2);font-variant-numeric:tabular-nums}
.rank-row .name{font-family:var(--mono);font-size:.85rem;overflow-wrap:anywhere}
.rank-row .track{height:10px;background:var(--line);border-radius:999px;overflow:hidden}
.rank-row .fill{display:block;height:100%;background:var(--bar);border-radius:999px}
.rank-row:first-child .fill{background:var(--bar-top)}
.rank-row .score{color:var(--ink-2);font-variant-numeric:tabular-nums;white-space:nowrap}
@media (max-width:560px){.rank-row{grid-template-columns:24px 1fr auto}.rank-row .track{grid-column:2/-1}}

.md{overflow-wrap:anywhere;max-width:72ch}
.md.raw{white-space:pre-wrap}
.md h1,.md h2,.md h3,.md h4{line-height:1.3;margin:1.5em 0 .5em;letter-spacing:-.005em}
.md h1{font-size:1.4rem}.md h2{font-size:1.2rem}.md h3{font-size:1.05rem}
.md p{margin:0 0 1em}.md ul,.md ol{padding-left:1.4em;margin:0 0 1em}.md li{margin:.25em 0}
.md a{color:var(--accent)}
.md blockquote{margin:0 0 1em;padding:.2em 1em;border-left:3px solid var(--line);color:var(--ink-2)}
.md code{font-family:var(--mono);font-size:.88em;background:var(--bg);padding:.1em .4em;border-radius:4px}
.md pre{overflow-x:auto;background:var(--bg);padding:12px 14px;border-radius:8px;margin:0 0 1em}
.md pre code{background:none;padding:0}
.md table{display:block;overflow-x:auto;border-collapse:collapse;margin:0 0 1em;font-size:.92rem}
.md th,.md td{border-bottom:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top}
.md th{font-weight:600;border-bottom:2px solid var(--line)}
.md hr{border:0;border-top:1px solid var(--line);margin:1.5em 0}

footer{margin-top:40px;color:var(--ink-2);font-size:.8rem;text-align:center}
@media print{body{background:#fff;padding:0}details.card:not([open])>.body{display:block}
  .answer{box-shadow:none}}
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


def _short(model: str) -> str:
    return model.split("/", 1)[-1]


def _label_map(stage1: List[Dict[str, Any]]) -> Dict[str, str]:
    return {f"Response {chr(65 + i)}": r["model"] for i, r in enumerate(stage1)}


def _answer(s3) -> str:
    return (
        '<section class="answer"><div class="answer-head"><h2>Council answer</h2>'
        f'<span>chairman: {escape(s3["model"])}</span></div>{_md(s3["response"])}</section>'
    )


def _stage1(stage1) -> str:
    items = "".join(
        f'<details class="card"><summary><span class="model">{escape(r["model"])}</span></summary>'
        f'<div class="body">{_md(r["response"])}</div></details>'
        for r in stage1
    )
    return (
        '<h3 class="section">Individual responses</h3>'
        f'<p class="hint">What each council member answered on its own.</p>{items}'
    )


def _stage2(stage1, stage2) -> str:
    l2m = _label_map(stage1)
    agg = calculate_aggregate_rankings(stage2, l2m)

    worst = max((a["average_rank"] for a in agg), default=1)
    rows = ""
    for i, a in enumerate(agg, 1):
        # lower average position is better -> longer bar
        pct = 100 if worst <= 1 else round(100 * (worst + 1 - a["average_rank"]) / worst)
        rows += (
            f'<div class="rank-row"><span class="pos">#{i}</span>'
            f'<span class="name">{escape(a["model"])}</span>'
            f'<span class="track"><span class="fill" style="width:{pct}%"></span></span>'
            f'<span class="score">avg {a["average_rank"]} &middot; {a["rankings_count"]} votes</span></div>'
        )
    ranking = f'<div class="rank">{rows}</div>' if rows else ""

    evals = ""
    for r in stage2:
        parsed = r.get("parsed_ranking") or []
        chips = "".join(
            f'<span class="chip">{i}. {escape(_short(l2m.get(p, p)))}</span>'
            for i, p in enumerate(parsed, 1)
        )
        evals += (
            f'<details class="card"><summary><span class="model">{escape(r["model"])}</span></summary>'
            f'<div class="body">{_md(r["ranking"])}'
            f'<div class="extract"><span>Extracted ranking:</span>{chips or " none parsed"}</div></div></details>'
        )
    return (
        '<h3 class="section">Aggregate peer ranking</h3>'
        '<p class="hint">Models reviewed the responses anonymously (Response A, B, …). '
        "Names are shown here for readability. Longer bar = ranked better.</p>"
        f"{ranking}"
        '<h3 class="section">Peer reviews</h3>'
        f'<p class="hint">Each model&rsquo;s full evaluation of the others.</p>{evals}'
    )


def render_conversation_html(conv: Dict[str, Any]) -> str:
    turns = ""
    n_models = 0
    for m in conv.get("messages", []):
        if m.get("role") == "user":
            turns += (
                f'<div class="turn"><div class="question"><small>Question</small>'
                f'{escape(m["content"])}</div>'
            )
        else:
            s1, s2, s3 = m.get("stage1") or [], m.get("stage2") or [], m.get("stage3")
            n_models = max(n_models, len(s1))
            turns += _answer(s3) if s3 else ""
            turns += _stage1(s1) if s1 else ""
            turns += _stage2(s1, s2) if s2 else ""
            turns += "</div>"
    title = escape(conv.get("title") or "Council report")
    created = escape(str(conv.get("created_at", ""))[:10])
    meta = " &middot; ".join(
        x for x in (created, f"{n_models} council models" if n_models else "") if x
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{CSS}</style></head><body><main>"
        f'<header class="top"><h1>{title}</h1><div class="meta">FortiAICouncil &middot; {meta}</div></header>'
        f"{turns}<footer>Generated by FortiAICouncil</footer></main>"
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.1.6/purify.min.js"></script>'
        f"<script>{JS}</script></body></html>"
    )
