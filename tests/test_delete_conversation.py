import pytest
from fastapi.testclient import TestClient

from backend import storage


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path / "conv"))


def test_storage_delete():
    storage.create_conversation("abc")
    assert storage.delete_conversation("abc") is True
    assert storage.get_conversation("abc") is None
    assert storage.delete_conversation("abc") is False


def test_api_delete():
    from backend.main import app

    c = TestClient(app)
    cid = c.post("/api/conversations", json={}).json()["id"]
    assert c.delete(f"/api/conversations/{cid}").status_code == 200
    assert c.get(f"/api/conversations/{cid}").status_code == 404
    assert c.delete(f"/api/conversations/{cid}").status_code == 404
