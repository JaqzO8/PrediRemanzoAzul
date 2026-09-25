import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "PrediRemanzoAzul"


@pytest.mark.asyncio
async def test_api_prediccion_hoy():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/prediccion/hoy")
    assert response.status_code == 200
    data = response.json()
    assert data["zona"] == "Remanzo Azul"
    assert "visitantes_estimados" in data
    assert "clima_estimado" in data


@pytest.mark.asyncio
async def test_api_prediccion_fecha():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/prediccion/fecha?fecha=2026-10-01")
    assert response.status_code == 200
    data = response.json()
    assert data["fecha"] == "2026-10-01"


@pytest.mark.asyncio
async def test_api_simulacion():
    payload = {
        "clima_estado": "soleado",
        "temperatura_c": 28.5,
        "probabilidad_lluvia_pct": 5.0,
        "es_fin_de_semana": True,
        "dia_semana": "domingo",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/prediccion/simulacion", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["visitantes_estimados"] > 0


@pytest.mark.asyncio
async def test_api_clima_actual():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/clima/actual")
    assert response.status_code == 200
    data = response.json()
    assert data["zona"] == "Remanzo Azul"
    assert "temperatura_c" in data


@pytest.mark.asyncio
async def test_api_historico():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/historico?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["registros"]) == 5


@pytest.mark.asyncio
async def test_api_historico_estadisticas():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/historico/estadisticas")
    assert response.status_code == 200
    data = response.json()
    assert data["total_registros"] > 0
    assert "promedio_visitantes" in data
