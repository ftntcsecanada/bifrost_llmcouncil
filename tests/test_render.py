from fastapi.testclient import TestClient

from backend import render, storage


def _conv():
    return {
        "id": "c1",
        "title": "Firewall <test>",
        "created_at": "2026-01-01T00:00:00",
        "messages": [
            {"role": "user", "content": "What is <b>UTM</b>?"},
            {
                "role": "assistant",
                "stage1": [
                    {"model": "m/one", "response": "answer one"},
                    {"model": "m/two", "response": "answer two"},
                ],
                "stage2": [
                    {
                        "model": "m/one",
                        "ranking": "Response B is best\nFINAL RANKING:\n1. Response B\n2. Response A",
                        "parsed_ranking": ["Response B", "Response A"],
                    }
                ],
                "stage3": {"model": "m/chair", "response": "final synthesis"},
            },
        ],
    }


def test_render_contains_stages_and_escapes():
    html = render.render_conversation_html(_conv())
    assert html.startswith("<!doctype html>")
    for s in ("answer one", "answer two", "final synthesis", "m/chair"):
        assert s in html
    assert "<b>UTM</b>" not in html and "&lt;b&gt;UTM&lt;/b&gt;" in html
    assert "Firewall &lt;test&gt;" in html


def test_render_deanonymizes_and_aggregates():
    html = render.render_conversation_html(_conv())
    # Response B -> m/two ranked first, so aggregate lists m/two before m/one
    agg = html[html.index("Aggregate"):]
    assert agg.index("m/two") < agg.index("m/one")


def test_export_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    from backend.main import app

    storage.create_conversation("c1")
    c = TestClient(app)
    r = c.get("/api/conversations/c1/export.html")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert c.get("/api/conversations/nope/export.html").status_code == 404
