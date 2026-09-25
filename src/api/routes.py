from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.clima.client import ClimaClient
from src.clima.models import ClimaActual, PronosticoHora, PronosticoDia, ClimaOverview
from src.datos.repository import VisitasRepository
from src.datos.models import FiltroVisitas, RespuestaHistorico, EstadisticasVisitas
from src.prediccion.engine import MotorPrediccion
from src.prediccion.models import (
    PrediccionRespuesta,
    SimulacionRequest,
)

router = APIRouter()

# Dependencias singleton
_clima_client = ClimaClient()
_visitas_repo = VisitasRepository()
_motor_prediccion = MotorPrediccion(clima_client=_clima_client, repository=_visitas_repo)


def get_motor() -> MotorPrediccion:
    return _motor_prediccion


def get_clima() -> ClimaClient:
    return _clima_client


def get_repo() -> VisitasRepository:
    return _visitas_repo


# ============================================================================
# Endpoints de Predicción de Visitantes
# ============================================================================


@router.get(
    "/prediccion/hoy",
    response_model=PrediccionRespuesta,
    summary="Predicción de visitantes para el día actual",
    tags=["Predicción"],
)
async def predecir_hoy(
    motor: MotorPrediccion = Depends(get_motor),
) -> PrediccionRespuesta:
    """Devuelve la cantidad estimada de visitantes que asistirán **hoy** a Remanzo Azul,

    cruzando las condiciones climáticas en tiempo real con el patrón histórico de afluencia.
    """
    try:
        return await motor.predecir_hoy()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al calcular la predicción de hoy: {str(e)}"
        )


@router.get(
    "/prediccion/fecha",
    response_model=PrediccionRespuesta,
    summary="Predicción de visitantes para una fecha específica",
    tags=["Predicción"],
)
async def predecir_fecha(
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    motor: MotorPrediccion = Depends(get_motor),
) -> PrediccionRespuesta:
    """Calcula la afluencia estimada de visitantes para una fecha específica en Remanzo Azul.

    Si la fecha está en el rango de los próximos 14 días, utiliza el pronóstico meteorológico extendido.
    """
    try:
        return await motor.predecir_fecha(fecha)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al calcular la predicción para {fecha}: {str(e)}"
        )


@router.post(
    "/prediccion/simulacion",
    response_model=PrediccionRespuesta,
    summary="Simulación interactiva de afluencia (What-If)",
    tags=["Predicción"],
)
async def simular_prediccion(
    req: SimulacionRequest,
    motor: MotorPrediccion = Depends(get_motor),
) -> PrediccionRespuesta:
    """Permite calcular la afluencia estimada variando manualmente las condiciones meteorológicas y el tipo de día."""
    try:
        return motor.predecir_simulacion(req)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error durante la simulación: {str(e)}"
        )


# ============================================================================
# Endpoints de Consulta de Clima
# ============================================================================


@router.get(
    "/clima/actual",
    response_model=ClimaActual,
    summary="Clima actual en Remanzo Azul",
    tags=["Clima"],
)
async def obtener_clima_actual(
    clima: ClimaClient = Depends(get_clima),
) -> ClimaActual:
    """Obtiene el clima actual observado para la zona turística Remanzo Azul."""
    try:
        return await clima.get_current_weather()
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"No fue posible consultar el clima actual: {str(e)}"
        )


@router.get(
    "/clima/horario",
    response_model=List[PronosticoHora],
    summary="Pronóstico horario para Remanzo Azul",
    tags=["Clima"],
)
async def obtener_pronostico_horario(
    hours: int = Query(24, ge=1, le=72, description="Número de horas a pronosticar (1-72)"),
    clima: ClimaClient = Depends(get_clima),
) -> List[PronosticoHora]:
    """Obtiene el pronóstico hora por hora para las próximas horas en Remanzo Azul."""
    try:
        return await clima.get_hourly_forecast(hours=hours)
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Error al obtener pronóstico horario: {str(e)}"
        )


@router.get(
    "/clima/proximos-dias",
    response_model=List[PronosticoDia],
    summary="Pronóstico diario para los próximos días",
    tags=["Clima"],
)
async def obtener_pronostico_diario(
    days: int = Query(7, ge=1, le=14, description="Número de días a pronosticar (1-14)"),
    clima: ClimaClient = Depends(get_clima),
) -> List[PronosticoDia]:
    """Obtiene el pronóstico día a día para los próximos días en Remanzo Azul."""
    try:
        return await clima.get_daily_forecast(days=days)
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Error al obtener pronóstico diario: {str(e)}"
        )


@router.get(
    "/clima/overview",
    response_model=ClimaOverview,
    summary="Resumen consolidado del clima",
    tags=["Clima"],
)
async def obtener_clima_overview(
    clima: ClimaClient = Depends(get_clima),
) -> ClimaOverview:
    """Obtiene el resumen consolidado de clima: actual, próximas 12 horas y próximos 5 días."""
    try:
        return await clima.get_weather_overview()
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Error al obtener overview del clima: {str(e)}"
        )


@router.get(
    "/clima/estado-api",
    summary="Estado de conectividad con la API de clima",
    tags=["Clima"],
)
async def verificar_estado_api_clima(
    clima: ClimaClient = Depends(get_clima),
) -> Dict[str, Any]:
    """Comprueba el estado de salud, latencia y disponibilidad de la API de clima existente."""
    return await clima.check_api_status()


# ============================================================================
# Endpoints de Consulta de Histórico de Visitas
# ============================================================================


@router.get(
    "/historico",
    response_model=RespuestaHistorico,
    summary="Consulta paginada del histórico de visitas",
    tags=["Histórico"],
)
async def consultar_historico(
    fecha_inicio: Optional[str] = Query(None, description="Filtro fecha mínima (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Filtro fecha máxima (YYYY-MM-DD)"),
    clima_estado: Optional[str] = Query(None, description="soleado, nublado, lluvioso, etc."),
    es_fin_de_semana: Optional[bool] = Query(None, description="true para sáb/dom"),
    es_feriado: Optional[bool] = Query(None, description="true para días festivos"),
    limit: int = Query(50, ge=1, le=1000, description="Cantidad de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    repo: VisitasRepository = Depends(get_repo),
) -> RespuestaHistorico:
    """Permite auditar y consultar los registros históricos de afluencia turística de Remanzo Azul."""
    filtro = FiltroVisitas(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        clima_estado=clima_estado,
        es_fin_de_semana=es_fin_de_semana,
        es_feriado=es_feriado,
        limit=limit,
        offset=offset,
    )
    return repo.obtener_todos(filtro)


@router.get(
    "/historico/estadisticas",
    response_model=EstadisticasVisitas,
    summary="Estadísticas globales del histórico de visitas",
    tags=["Histórico"],
)
async def obtener_estadisticas_historico(
    repo: VisitasRepository = Depends(get_repo),
) -> EstadisticasVisitas:
    """Devuelve métricas agregadas: promedios por clima, día de semana, mínimos y máximos."""
    return repo.obtener_estadisticas()
