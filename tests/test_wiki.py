import pytest
from fastapi.testclient import TestClient

from backend import wiki


@pytest.fixture(autouse=True)
def wiki_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki, "WIKI_DIR", str(tmp_path / "wiki"))
    return tmp_path / "wiki"


def test_save_and_list():
    wiki.save_file("SKILL.md", b"# Skill\nbe precise")
    files = wiki.list_files()
    assert [f["name"] for f in files] == ["SKILL.md"]
    assert files[0]["size"] == len(b"# Skill\nbe precise")


def test_rejects_bad_extension():
    with pytest.raises(ValueError):
        wiki.save_file("evil.exe", b"x")


def test_rejects_path_traversal_by_using_basename(wiki_dir):
    wiki.save_file("../../escape.md", b"x")
    assert (wiki_dir / "escape.md").exists()


def test_rejects_non_utf8():
    with pytest.raises(ValueError):
        wiki.save_file("a.md", b"\xff\xfe\x00bad")


def test_delete():
    wiki.save_file("a.md", b"x")
    assert wiki.delete_file("a.md") is True
    assert wiki.delete_file("a.md") is False


def test_build_context_empty():
    assert wiki.build_context() == ""


def test_build_context_orders_skill_first_and_labels_files():
    wiki.save_file("b.md", b"page b")
    wiki.save_file("SKILL.md", b"skill text")
    ctx = wiki.build_context()
    assert ctx.index("SKILL.md") < ctx.index("b.md")
    assert "skill text" in ctx and "page b" in ctx


def test_build_context_caps_size():
    wiki.save_file("big.md", b"x" * 500)
    ctx = wiki.build_context(max_chars=100)
    assert len(ctx) <= 100 + 200  # cap on content plus small header/notice
    assert "truncated" in ctx


def test_api_upload_list_delete():
    from backend.main import app

    c = TestClient(app)
    r = c.post("/api/wiki", files={"file": ("SKILL.md", b"hello", "text/markdown")})
    assert r.status_code == 200
    assert [f["name"] for f in c.get("/api/wiki").json()] == ["SKILL.md"]
    assert c.post("/api/wiki", files={"file": ("x.exe", b"1")}).status_code == 400
    assert c.delete("/api/wiki/SKILL.md").status_code == 200
    assert c.delete("/api/wiki/SKILL.md").status_code == 404
