"""
Tests for the CORS allow-list in app/main.py. A browser silently discards
any response missing Access-Control-Allow-Origin for its page's origin, so
the deployed frontend shows "Failed to fetch" even when the API itself is up.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "https://transit-improvement-lab.vercel.app"],
)
def test_allowed_origins_get_cors_header(origin):
    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_unknown_origin_gets_no_cors_header():
    response = client.get("/health", headers={"Origin": "https://example.com"})

    assert "access-control-allow-origin" not in response.headers
