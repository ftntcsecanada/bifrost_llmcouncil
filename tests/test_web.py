import asyncio

import pytest

from backend import web, wiki


@pytest.fixture(autouse=True)
def reset(monkeypatch, tmp_path):
    monkeypatch.setattr(wiki, "WIKI_DIR", str(tmp_path / "wiki"))
    web.web_context.set("")
    yield
    web.web_context.set("")


RESULTS = [{"title": "T1", "href": "https://a.example/1", "body": "snippet one"}]


def test_format_context_has_urls_and_instruction():
    ctx = web.format_context(RESULTS)
    assert "https://a.example/1" in ctx and "snippet one" in ctx
    assert "cite" in ctx.lower()


def test_apply_web_only_for_allowed_models(monkeypatch):
    monkeypatch.setattr(web, "WEB_SEARCH_MODELS", ["m/yes"])
    web.web_context.set("<web>X</web>")
    msgs = [{"role": "user", "content": "q"}]
    assert "<web>X</web>" in web.apply_web("m/yes", msgs)[0]["content"]
    assert web.apply_web("m/no", msgs) == msgs
    assert msgs[0]["content"] == "q"  # original not mutated


def test_apply_web_noop_without_context(monkeypatch):
    monkeypatch.setattr(web, "WEB_SEARCH_MODELS", ["m/yes"])
    msgs = [{"role": "user", "content": "q"}]
    assert web.apply_web("m/yes", msgs) == msgs


def test_search_failure_returns_empty(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network")

    monkeypatch.setattr(web, "_ddg_text", boom)
    assert asyncio.run(web.search("q")) == []


def test_prepare_disabled_does_nothing(monkeypatch):
    called = []
    monkeypatch.setattr(web, "wiki_covers", lambda q: called.append(q) or False)
    assert asyncio.run(web.prepare("q", enabled=False)) == []
    assert called == [] and web.web_context.get() == ""


def test_prepare_skips_search_when_wiki_covers(monkeypatch):
    async def covers(q):
        return True

    monkeypatch.setattr(web, "wiki_covers", covers)
    assert asyncio.run(web.prepare("q", enabled=True)) == []
    assert web.web_context.get() == ""


def test_prepare_searches_when_not_covered(monkeypatch):
    async def covers(q):
        return False

    async def fake_search(q, n=5):
        return RESULTS

    monkeypatch.setattr(web, "wiki_covers", covers)
    monkeypatch.setattr(web, "search", fake_search)
    async def run():
        # context var is set inside the same task chain the council stages run in
        return await web.prepare("q", enabled=True), web.web_context.get()

    sources, ctx = asyncio.run(run())
    assert sources == [{"title": "T1", "url": "https://a.example/1"}]
    assert "snippet one" in ctx


def test_wiki_covers_false_without_wiki():
    assert asyncio.run(web.wiki_covers("anything")) is False


def test_wiki_covers_parses_yes_no(monkeypatch):
    wiki.save_file("a.md", b"firewall policy")

    async def fake_query(model, messages, **k):
        return {"content": fake_query.answer}

    monkeypatch.setattr(web, "query_model", fake_query)
    fake_query.answer = "YES"
    assert asyncio.run(web.wiki_covers("firewall policy")) is True
    fake_query.answer = "no, not covered"
    assert asyncio.run(web.wiki_covers("firewall policy")) is False
    monkeypatch.setattr(web, "query_model", lambda *a, **k: asyncio.sleep(0, result=None))
    assert asyncio.run(web.wiki_covers("firewall policy")) is False  # failed call -> not covered
