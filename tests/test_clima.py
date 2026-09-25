import pytest
from src.clima.models import mapear_codigo_wmo, ClimaEstadoEnum
from src.clima.client import ClimaClient


def test_mapeo_codigos_wmo():
    assert mapear_codigo_wmo(0) == ClimaEstadoEnum.SOLEADO.value
    assert mapear_codigo_wmo(1) == ClimaEstadoEnum.SOLEADO.value
    assert mapear_codigo_wmo(2) == ClimaEstadoEnum.PARCIALMENTE_NUBLADO.value
    assert mapear_codigo_wmo(3) == ClimaEstadoEnum.NUBLADO.value
    assert mapear_codigo_wmo(61) == ClimaEstadoEnum.LLUVIOSO.value
    assert mapear_codigo_wmo(80) == ClimaEstadoEnum.LLUVIOSO.value
    assert mapear_codigo_wmo(95) == ClimaEstadoEnum.TORMENTA.value
    assert mapear_codigo_wmo(999, "tormenta fuerte") == ClimaEstadoEnum.TORMENTA.value


@pytest.mark.asyncio
async def test_clima_client_fallback():
    client = ClimaClient()
    # Debe responder aún si la API local primaria no está corriendo gracias a su fallback
    clima = await client.get_current_weather()
    assert clima is not None
    assert clima.temperatura_c > -20
    assert clima.estado in [e.value for e in ClimaEstadoEnum]
    assert clima.fuente != ""


@pytest.mark.asyncio
async def test_pronostico_diario():
    client = ClimaClient()
    dias = await client.get_daily_forecast(days=5)
    assert len(dias) >= 1
    assert dias[0].temperatura_max_c >= dias[0].temperatura_min_c
