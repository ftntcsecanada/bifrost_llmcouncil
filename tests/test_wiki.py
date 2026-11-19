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


# --- folder support & relevance selection ---

def test_nested_paths_preserved_and_no_collision(wiki_dir):
    wiki.save_file("a/overview.md", b"A")
    wiki.save_file("b/overview.md", b"B")
    assert [f["name"] for f in wiki.list_files()] == ["a/overview.md", "b/overview.md"]
    assert (wiki_dir / "a" / "overview.md").read_text() == "A"


def test_traversal_segments_stripped(wiki_dir):
    wiki.save_file("x/../../y/./z.md", b"x")
    assert (wiki_dir / "x" / "y" / "z.md").exists()


def test_delete_nested():
    wiki.save_file("a/b.md", b"x")
    assert wiki.delete_file("a/b.md") is True
    assert wiki.list_files() == []


def test_context_selects_relevant_pages_when_over_cap():
    wiki.save_file("index.md", b"# Index\n- firewall\n- cooking")
    wiki.save_file("topics/firewall.md", b"firewall policy rules " * 10)
    wiki.save_file("topics/cooking.md", b"pasta sauce recipes " * 10)
    ctx = wiki.build_context(max_chars=400, query="how do firewall policy rules work?")
    assert "topics/firewall.md" in ctx
    assert "topics/cooking.md" not in ctx
    assert "index.md" in ctx


def test_context_full_when_fits_even_with_query():
    wiki.save_file("a.md", b"alpha")
    wiki.save_file("b.md", b"beta")
    ctx = wiki.build_context(max_chars=1000, query="alpha")
    assert "alpha" in ctx and "beta" in ctx


def test_api_nested_upload_and_delete():
    from backend.main import app

    c = TestClient(app)
    r = c.post("/api/wiki", files={"file": ("sub/p.md", b"hi", "text/markdown")})
    assert r.status_code == 200 and r.json()["name"] == "sub/p.md"
    assert c.delete("/api/wiki/sub/p.md").status_code == 200
