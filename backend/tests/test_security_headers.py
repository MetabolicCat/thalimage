"""No response may be framed or have its type sniffed (SEC-004)."""

from fastapi.testclient import TestClient


def test_the_spa_and_api_carry_the_headers(client: TestClient) -> None:
    for path in ("/", "/api/v1/version"):
        resp = client.get(path)
        assert resp.headers["content-security-policy"] == "frame-ancestors 'none'"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["x-content-type-options"] == "nosniff"


def test_a_refused_write_carries_them_too(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/tags", json={"name": "x"}, headers={"origin": "https://evil.example"}
    )
    assert resp.status_code == 403
    assert resp.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-content-type-options"] == "nosniff"
