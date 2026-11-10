"""HTTP API tests (need fastapi + httpx, installed via requirements-dev.txt)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from reviewops.main import app  # noqa: E402

client = TestClient(app)

BAD_DIFF = "@@ -1,1 +1,2 @@\n x = 1\n+API_KEY = \"abcd1234\"\n"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_review_blocks_hardcoded_secret():
    r = client.post("/review", json={"repo": "demo/app", "pr_number": 7, "diff": BAD_DIFF})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "block"
    assert body["comments"][0]["rule"] == "hardcoded-secret"


def test_review_rejects_empty_diff():
    assert client.post("/review", json={"diff": ""}).status_code == 422


def test_ui_shows_version_badge_and_history():
    client.post("/review", json={"repo": "demo/app", "diff": BAD_DIFF})
    page = client.get("/").text
    assert "version" in page
    assert "demo/app" in page
    assert len(client.get("/reviews").json()) >= 1
