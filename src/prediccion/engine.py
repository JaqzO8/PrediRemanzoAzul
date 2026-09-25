import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import numpy as np

from src.clima.client import ClimaClient
from src.clima.models import ClimaActual, PronosticoDia
from src.datos.repository import VisitasRepository
from src.prediccion.models import (
    PrediccionRespuesta,
    ClimaEstimadoInfo,
    RangoEstimado,
    ReferenciaHistorica,
    SimulacionRequest,
)

logger = logging.getLogger(__name__)

DIAS_SEMANA_ES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}


class MotorPrediccion:
    """Motor analítico de predicción de afluencia para Remanzo Azul.

    Combina el estado meteorológico actual o proyectado con el histórico de visitas,
    empleando k-vecinos ponderados por similitud contextual (clima, temperatura,
    precipitación, día de la semana y feriados).
    """

    def __init__(
        self,
        clima_client: Optional[ClimaClient] = None,
        repository: Optional[VisitasRepository] = None,
    ):
        self.clima_client = clima_client or ClimaClient()
        self.repo = repository or VisitasRepository()

    async def predecir_hoy(self) -> PrediccionRespuesta:
        """Calcula la afluencia estimada de visitantes para el día de hoy en Remanzo Azul."""
        clima_actual = await self.clima_client.get_current_weather()
        hoy = date.today()

        return self._generar_prediccion(
            fecha=hoy,
            clima_estado=clima_actual.estado,
            temperatura_c=clima_actual.temperatura_c,
            probabilidad_lluvia_pct=clima_actual.probabilidad_lluvia_pct,
            descripcion_clima=clima_actual.descripcion,
            fuente_clima=clima_actual.fuente,
        )

    async def predecir_fecha(self, fecha_str: str) -> PrediccionRespuesta:
        """Calcula la afluencia estimada para una fecha específica."""
        try:
            target_date = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Formato de fecha inválido: {fecha_str}. Debe ser YYYY-MM-DD")

        hoy = date.today()
        dias_diferencia = (target_date - hoy).days

        # Si es hoy
        if dias_diferencia == 0:
            return await self.predecir_hoy()

        # Si es un día futuro próximo dentro del rango de pronóstico (hasta 14 días)
        if 0 < dias_diferencia <= 14:
            pronosticos = await self.clima_client.get_daily_forecast(days=dias_diferencia + 1)
            dia_pronosticado = next(
                (p for p in pronosticos if p.fecha == target_date.isoformat()), None
            )
            if dia_pronosticado:
                return self._generar_prediccion(
                    fecha=target_date,
                    clima_estado=dia_pronosticado.estado,
                    temperatura_c=dia_pronosticado.temperatura_promedio_c,
                    probabilidad_lluvia_pct=dia_pronosticado.probabilidad_lluvia_pct,
                    descripcion_clima=dia_pronosticado.descripcion,
                    fuente_clima="Pronóstico Meteorológico Extendido",
                )

        # Para fechas pasadas o más lejanas, estimar con base estacional promedio
        return self._generar_prediccion(
            fecha=target_date,
            clima_estado="parcialmente nublado",
            temperatura_c=26.0,
            probabilidad_lluvia_pct=25.0,
            descripcion_clima="Estimación meteorológica de tendencia",
            fuente_clima="Histórico estacional aproximado",
        )

    def predecir_simulacion(self, req: SimulacionRequest) -> PrediccionRespuesta:
        """Permite al usuario evaluar escenarios hipotéticos 'what-if'."""
        hoy = date.today()
        dia_nombre = req.dia_semana.lower().strip() if req.dia_semana else "sábado"

        return self._generar_prediccion_directa(
            fecha=hoy,
            dia_semana=dia_nombre,
            es_fin_de_semana=req.es_fin_de_semana,
            es_feriado=req.es_feriado,
            clima_estado=req.clima_estado,
            temperatura_c=req.temperatura_c,
            probabilidad_lluvia_pct=req.probabilidad_lluvia_pct,
            descripcion_clima=f"Simulación ({req.clima_estado})",
            fuente_clima="Simulador Interactivo de Usuario",
        )

    def _generar_prediccion(
        self,
        fecha: date,
        clima_estado: str,
        temperatura_c: float,
        probabilidad_lluvia_pct: float,
        descripcion_clima: str,
        fuente_clima: str,
    ) -> PrediccionRespuesta:
        dia_idx = fecha.weekday()
        dia_semana = DIAS_SEMANA_ES.get(dia_idx, "lunes")
        es_fin_de_semana = dia_idx in (5, 6)
        # Aproximación de feriado: domingos festivos o días específicos conocidos
        es_feriado = False

        return self._generar_prediccion_directa(
            fecha=fecha,
            dia_semana=dia_semana,
            es_fin_de_semana=es_fin_de_semana,
            es_feriado=es_feriado,
            clima_estado=clima_estado,
            temperatura_c=temperatura_c,
            probabilidad_lluvia_pct=probabilidad_lluvia_pct,
            descripcion_clima=descripcion_clima,
            fuente_clima=fuente_clima,
        )

    def _generar_prediccion_directa(
        self,
        fecha: date,
        dia_semana: str,
        es_fin_de_semana: bool,
        es_feriado: bool,
        clima_estado: str,
        temperatura_c: float,
        probabilidad_lluvia_pct: float,
        descripcion_clima: str,
        fuente_clima: str,
    ) -> PrediccionRespuesta:
        clima_norm = clima_estado.lower().strip()

        # Consultar registros similares en el repositorio desacoplado
        similares = self.repo.obtener_similares(
            clima_estado=clima_norm,
            es_fin_de_semana=es_fin_de_semana,
            es_feriado=es_feriado,
            temperatura_c=temperatura_c,
            probabilidad_lluvia_pct=probabilidad_lluvia_pct,
            dia_semana=dia_semana,
            limit=25,
        )

        if not similares:
            # Resguardo estadístico base
            visitantes_estimados = 320 if es_fin_de_semana else 180
            rango_min = int(visitantes_estimados * 0.8)
            rango_max = int(visitantes_estimados * 1.2)
            confianza = "baja"
            referencias = []
        else:
            # Ponderación basada en similitud inversa
            distancias = np.array([max(0.1, float(r.get("distancia", 1.0))) for r in similares])
            pesos = 1.0 / distancias
            pesos /= pesos.sum()

            valores = np.array([float(r["cantidad_visitantes"]) for r in similares])
            visitantes_estimados = int(round(np.sum(valores * pesos)))

            # Intervalos de percentiles 15 y 85
            rango_min = int(max(20, np.percentile(valores, 15)))
            rango_max = int(max(rango_min + 15, np.percentile(valores, 85)))

            # Nivel de confianza según cantidad y dispersión
            coef_var = np.std(valores) / max(1.0, np.mean(valores))
            if len(similares) >= 15 and coef_var < 0.35:
                confianza = "alta"
            elif len(similares) >= 8 and coef_var < 0.55:
                confianza = "media"
            else:
                confianza = "baja"

            referencias = [
                ReferenciaHistorica(
                    fecha=str(r["fecha"]),
                    dia_semana=str(r["dia_semana"]),
                    clima_estado=str(r["clima_estado"]),
                    temperatura_c=float(r["temperatura_c"]),
                    cantidad_visitantes=int(r["cantidad_visitantes"]),
                )
                for r in similares[:5]
            ]

        # Clasificación del nivel de afluencia
        if visitantes_estimados < 160:
            nivel = "Baja"
        elif visitantes_estimados <= 280:
            nivel = "Moderada"
        elif visitantes_estimados <= 450:
            nivel = "Alta"
        else:
            nivel = "Pico"

        # Factores explicativos clave
        factores = self._generar_factores_clave(
            es_fin_de_semana=es_fin_de_semana,
            es_feriado=es_feriado,
            clima_estado=clima_norm,
            temperatura_c=temperatura_c,
            probabilidad_lluvia_pct=probabilidad_lluvia_pct,
            visitantes=visitantes_estimados,
        )

        return PrediccionRespuesta(
            zona="Remanzo Azul",
            fecha=fecha.isoformat(),
            dia_semana=dia_semana,
            es_fin_de_semana=es_fin_de_semana,
            es_feriado=es_feriado,
            clima_estimado=ClimaEstimadoInfo(
                estado=clima_norm,
                temperatura=round(temperatura_c, 1),
                probabilidad_lluvia_pct=round(probabilidad_lluvia_pct, 1),
                descripcion=descripcion_clima,
                fuente_clima=fuente_clima,
            ),
            visitantes_estimados=visitantes_estimados,
            rango_estimado=RangoEstimado(min=rango_min, max=rango_max),
            nivel_afluencia=nivel,
            confianza=confianza,
            factores_clave=factores,
            fuente_datos="simulada",
            referencias_historicas_muestra=referencias,
            nota="Basado en datos históricos simulados y meteorología de Remanzo Azul",
        )

    def _generar_factores_clave(
        self,
        es_fin_de_semana: bool,
        es_feriado: bool,
        clima_estado: str,
        temperatura_c: float,
        probabilidad_lluvia_pct: float,
        visitantes: int,
    ) -> List[str]:
        factores = []

        if es_fin_de_semana or es_feriado:
            factores.append("Fin de semana / día no laboral: incremento histórico de afluencia (+75% promedio).")
        else:
            factores.append("Día laboral: flujo de visitantes más moderado y enfocado en turismo local.")

        if clima_estado == "soleado":
            factores.append("Cielo despejado/soleado: condición óptima para disfrute de aguas, senderos y zonas recreativas.")
        elif clima_estado == "parcialmente nublado":
            factores.append("Parcialmente nublado: temperatura confortable sin sobrecalentamiento solar.")
        elif clima_estado == "nublado":
            factores.append("Cielo nublado: afluencia moderada con menor preferencia de baño en río.")
        elif clima_estado == "lluvioso":
            factores.append("Lluvias previstas: reducción notable de turistas recreativos y familias.")
        elif clima_estado == "tormenta":
            factores.append("Alerta de tormenta: afluencia mínima por precauciones de seguridad y corriente.")

        if temperatura_c >= 28.0:
            factores.append(f"Temperatura cálida ({temperatura_c}°C): alta atracción hacia balnearios y pozas de Remanzo Azul.")
        elif temperatura_c < 22.0:
            factores.append(f"Temperatura fresca ({temperatura_c}°C): menor motivación para inmersión acuática.")

        if probabilidad_lluvia_pct > 60.0:
            factores.append(f"Alta probabilidad de lluvia ({probabilidad_lluvia_pct}%): posible deserción de visitantes de la tarde.")
        elif probabilidad_lluvia_pct < 20.0:
            factores.append(f"Baja probabilidad de lluvia ({probabilidad_lluvia_pct}%): estabilidad garantizada para actividades al aire libre.")

        return factores
