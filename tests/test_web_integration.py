import asyncio

from backend import bifrost, web


def test_query_model_sends_web_context_only_to_allowed(monkeypatch):
    sent = {}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "ok"}}]}

    class FakeClient:
        def __init__(self, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers, json):
            sent["content"] = json["messages"][0]["content"]
            return FakeResp()

    monkeypatch.setattr(bifrost.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(web, "WEB_SEARCH_MODELS", ["m/yes"])

    async def run(model):
        web.web_context.set("<web>CTX</web>")
        await bifrost.query_model(model, [{"role": "user", "content": "q"}])
        return sent["content"]

    assert "<web>CTX</web>" in asyncio.run(run("m/yes"))
    assert asyncio.run(run("m/no")) == "q"
