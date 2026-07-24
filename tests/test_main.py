from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from backend.main import create_app


async def test_health_check() -> None:
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "name": "产品管理智能助手平台",
        "version": "1.0.0",
        "environment": "development",
    }
