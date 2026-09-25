import pytest
from src.prediccion.engine import MotorPrediccion
from src.prediccion.models import SimulacionRequest


@pytest.fixture
def motor():
    return MotorPrediccion()


@pytest.mark.asyncio
async def test_prediccion_hoy(motor):
    pred = await motor.predecir_hoy()
    assert pred.zona == "Remanzo Azul"
    assert pred.visitantes_estimados > 0
    assert pred.rango_estimado.min <= pred.visitantes_estimados <= pred.rango_estimado.max
    assert pred.confianza in ("alta", "media", "baja")
    assert len(pred.factores_clave) > 0
    assert pred.fuente_datos == "simulada"


@pytest.mark.asyncio
async def test_prediccion_fecha_futura(motor):
    pred = await motor.predecir_fecha("2026-10-15")
    assert pred.fecha == "2026-10-15"
    assert pred.visitantes_estimados > 0


def test_prediccion_simulacion_soleado_vs_lluvia(motor):
    req_soleado = SimulacionRequest(
        clima_estado="soleado",
        temperatura_c=30.0,
        probabilidad_lluvia_pct=0.0,
        es_fin_de_semana=True,
    )
    res_soleado = motor.predecir_simulacion(req_soleado)

    req_lluvioso = SimulacionRequest(
        clima_estado="lluvioso",
        temperatura_c=22.0,
        probabilidad_lluvia_pct=90.0,
        es_fin_de_semana=False,
    )
    res_lluvioso = motor.predecir_simulacion(req_lluvioso)

    # El día soleado de fin de semana debe tener significativamente más visitantes que un día lluvioso laboral
    assert res_soleado.visitantes_estimados > res_lluvioso.visitantes_estimados
