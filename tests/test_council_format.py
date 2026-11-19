import asyncio

from backend import council


def test_stage1_and_chairman_prompts_forbid_tables(monkeypatch):
    seen = []

    async def fake_parallel(models, messages):
        seen.append(messages[0]["content"])
        return {}

    async def fake_query(model, messages, **k):
        seen.append(messages[0]["content"])
        return {"content": "x"}

    monkeypatch.setattr(council, "query_models_parallel", fake_parallel)
    monkeypatch.setattr(council, "query_model", fake_query)
    monkeypatch.setattr(council, "with_context", lambda p, q=None: p)

    asyncio.run(council.stage1_collect_responses("q"))
    asyncio.run(council.stage3_synthesize_final("q", [{"model": "a/b", "response": "r"}], []))
    assert len(seen) == 2
    assert all(council.NO_TABLES in s for s in seen)
