from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from models import Recipe


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_recommend_validates_short_token() -> None:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/recommend",
            json={"mode": "daily", "navigator_token": "short"},
        )

    assert response.status_code == 400
    assert "token" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_recommend_success_with_mocked_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_recommendations(_request, trace=None):
        if trace:
            trace.update("vector_db", {"query_text": "test query", "kept_titles": ["Shakshuka"]})
        return (
            [
                Recipe(
                    title="Shakshuka",
                    emoji="🍳",
                    time=25,
                    servings=2,
                    calories=380,
                    ingredients=["eggs", "tomatoes", "garlic"],
                    steps=["Simmer sauce.", "Poach eggs."],
                    tags=["Vegetarian", "Quick"],
                    description="Eggs in tomato sauce.",
                    match_reason="Uses the selected ingredients.",
                )
            ],
            5,
        )

    monkeypatch.setattr(main, "get_recommendations", fake_get_recommendations)
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/recommend",
            json={
                "mode": "ingredients",
                "navigator_token": "test-token-12345",
                "ingredients": ["eggs", "tomatoes"],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_count"] == 5
    assert body["recipes"][0]["title"] == "Shakshuka"
    assert response.headers["x-trace-id"]


@pytest.mark.asyncio
async def test_admin_traces_lists_saved_request() -> None:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/traces")

    assert response.status_code == 200
    assert "traces" in response.json()


@pytest.mark.asyncio
async def test_admin_trace_report_returns_readable_sections() -> None:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        traces_response = await client.get("/admin/traces")
        request_id = traces_response.json()["traces"][0]["request_id"]
        report_response = await client.get(f"/admin/traces/{request_id}/report")

    assert report_response.status_code == 200
    assert "Vector DB / Retrieval" in report_response.text
    assert "Augmentation" in report_response.text
    assert "LLM Generation" in report_response.text


@pytest.mark.asyncio
async def test_admin_observability_ui_returns_dashboard() -> None:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/observability")

    assert response.status_code == 200
    assert "RAG Observability" in response.text
    assert "LLM" in response.text


@pytest.mark.asyncio
async def test_admin_trace_ui_returns_human_sections() -> None:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        traces_response = await client.get("/admin/traces")
        request_id = traces_response.json()["traces"][0]["request_id"]
        response = await client.get(f"/admin/traces/{request_id}/ui")

    assert response.status_code == 200
    assert "Vector DB Retrieval" in response.text
    assert "Augmentation" in response.text
    assert "LLM Generation" in response.text
