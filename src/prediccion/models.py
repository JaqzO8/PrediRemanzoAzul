from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ClimaEstimadoInfo(BaseModel):
    """Información del clima usada para la predicción."""
    estado: str
    temperatura: float
    probabilidad_lluvia_pct: float = 0.0
    descripcion: str = ""
    fuente_clima: str = "API-Clima"


class RangoEstimado(BaseModel):
    min: int
    max: int


class ReferenciaHistorica(BaseModel):
    fecha: str
    dia_semana: str
    clima_estado: str
    temperatura_c: float
    cantidad_visitantes: int


class PrediccionRespuesta(BaseModel):
    """Estructura de respuesta de predicción compatible con la especificación técnica."""
    zona: str = "Remanzo Azul"
    fecha: str
    dia_semana: str
    es_fin_de_semana: bool
    es_feriado: bool
    clima_estimado: ClimaEstimadoInfo
    visitantes_estimados: int
    rango_estimado: RangoEstimado
    nivel_afluencia: str = Field(description="Baja, Moderada, Alta, Pico")
    confianza: str = Field(description="alta, media, baja")
    factores_clave: List[str]
    fuente_datos: str = "simulada"
    referencias_historicas_muestra: List[ReferenciaHistorica] = Field(default_factory=list)
    nota: str = "Predicción generada mediante cruce de clima en tiempo real y comportamiento histórico"


class SimulacionRequest(BaseModel):
    """Parámetros para simulación hipotética 'what-if'."""
    clima_estado: str = Field(default="soleado", description="soleado, parcialmente nublado, nublado, lluvioso, tormenta")
    temperatura_c: float = Field(default=27.0, ge=10.0, le=45.0)
    probabilidad_lluvia_pct: float = Field(default=10.0, ge=0.0, le=100.0)
    es_fin_de_semana: bool = True
    es_feriado: bool = False
    dia_semana: Optional[str] = "sábado"
