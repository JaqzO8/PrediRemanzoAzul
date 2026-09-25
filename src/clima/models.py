from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ClimaEstadoEnum(str, Enum):
    SOLEADO = "soleado"
    PARCIALMENTE_NUBLADO = "parcialmente nublado"
    NUBLADO = "nublado"
    LLUVIOSO = "lluvioso"
    TORMENTA = "tormenta"


def mapear_codigo_wmo(codigo: int, descripcion: str = "") -> str:
    """Mapea un código WMO estándar (o texto) a uno de los 5 estados canónicos del histórico."""
    desc = (descripcion or "").lower()

    if codigo in (95, 96, 99) or "tormenta" in desc or "trueno" in desc:
        return ClimaEstadoEnum.TORMENTA.value

    if codigo in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86) or "lluv" in desc or "chubasco" in desc or "llovizna" in desc:
        return ClimaEstadoEnum.LLUVIOSO.value

    if codigo in (3, 45, 48) or "cubierto" in desc or "niebla" in desc:
        return ClimaEstadoEnum.NUBLADO.value

    if codigo == 2 or "parcial" in desc or "intervalos" in desc:
        return ClimaEstadoEnum.PARCIALMENTE_NUBLADO.value

    if codigo in (0, 1) or "despejado" in desc or "sol" in desc or "claro" in desc:
        return ClimaEstadoEnum.SOLEADO.value

    # Fallback por defecto según descripción o soleado
    if "nub" in desc:
        return ClimaEstadoEnum.NUBLADO.value

    return ClimaEstadoEnum.SOLEADO.value


class ClimaActual(BaseModel):
    """Datos climáticos actuales para la zona de interés."""
    zona: str = "Remanzo Azul"
    estado: str = Field(description="Estado climático canónico: soleado, parcialmente nublado, nublado, lluvioso, tormenta")
    temperatura_c: float
    probabilidad_lluvia_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    humedad_relativa_pct: Optional[int] = None
    viento_kmh: Optional[float] = None
    codigo_wmo: int = 0
    descripcion: str = ""
    fuente: str = "API-Clima"
    hora_observacion: str = ""


class PronosticoHora(BaseModel):
    """Pronóstico horario."""
    hora: str
    temperatura_c: float
    probabilidad_lluvia_pct: float
    estado: str
    descripcion: str
    viento_kmh: Optional[float] = None


class PronosticoDia(BaseModel):
    """Pronóstico diario para próximos días."""
    fecha: str
    temperatura_max_c: float
    temperatura_min_c: float
    temperatura_promedio_c: float
    probabilidad_lluvia_pct: float
    estado: str
    descripcion: str
    viento_max_kmh: Optional[float] = None


class ClimaOverview(BaseModel):
    """Resumen completo del clima: actual, horario y próximos días."""
    zona: str = "Remanzo Azul"
    fuente: str
    actual: ClimaActual
    proximas_horas: List[PronosticoHora] = Field(default_factory=list)
    proximos_dias: List[PronosticoDia] = Field(default_factory=list)
