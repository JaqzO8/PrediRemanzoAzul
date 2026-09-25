from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class VisitaRegistro(BaseModel):
    """Representa un registro individual de afluencia turística en Remanzo Azul."""
    id: int
    fecha: str
    dia_semana: str
    es_fin_de_semana: bool
    es_feriado: bool
    clima_estado: str
    temperatura_c: float
    probabilidad_lluvia_pct: float
    cantidad_visitantes: int
    zona: str = "Remanzo Azul"


class FiltroVisitas(BaseModel):
    """Parámetros de búsqueda y filtrado en el histórico de visitas."""
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    clima_estado: Optional[str] = None
    es_fin_de_semana: Optional[bool] = None
    es_feriado: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class EstadisticasVisitas(BaseModel):
    """Estadísticas descriptivas consolidadas sobre el comportamiento histórico."""
    total_registros: int
    fecha_minima: str
    fecha_maxima: str
    promedio_visitantes: float
    mediana_visitantes: float
    min_visitantes: int
    max_visitantes: int
    desviacion_estandar: float
    promedio_fin_de_semana: float
    promedio_dia_semana: float
    promedio_feriados: float
    promedio_por_clima: Dict[str, float]
    promedio_por_dia_semana: Dict[str, float]
    distribucion_clima: Dict[str, int]


class RespuestaHistorico(BaseModel):
    """Respuesta paginada del histórico de visitas."""
    total: int
    limit: int
    offset: int
    registros: List[VisitaRegistro]
