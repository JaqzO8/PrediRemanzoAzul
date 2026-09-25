import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from src.config.settings import Settings, get_settings
from src.datos.models import (
    VisitaRegistro,
    FiltroVisitas,
    EstadisticasVisitas,
    RespuestaHistorico,
)

logger = logging.getLogger(__name__)


class VisitasRepository:
    """Repositorio desacoplado para consultar el histórico de visitas a Remanzo Azul.

    Diseñado para poder sustituirse en el futuro por una base de datos SQL
    (PostgreSQL/SQLite) o un servicio externo sin modificar la lógica de predicción.
    """

    def __init__(self, settings: Optional[Settings] = None, csv_path: Optional[Path] = None):
        self.settings = settings or get_settings()
        self.csv_path = csv_path or self.settings.resolve_csv_path()
        self._df: Optional[pd.DataFrame] = None
        self._cargar_datos()

    def _cargar_datos(self) -> None:
        """Carga y limpia el dataset histórico de visitas."""
        if not self.csv_path.exists():
            logger.error(f"Archivo histórico no encontrado en {self.csv_path}")
            # Crear un dataframe mínimo de resguardo
            self._df = pd.DataFrame(
                columns=[
                    "fecha",
                    "dia_semana",
                    "es_fin_de_semana",
                    "es_feriado",
                    "clima_estado",
                    "temperatura_c",
                    "probabilidad_lluvia_pct",
                    "cantidad_visitantes",
                    "zona",
                ]
            )
            return

        try:
            df = pd.read_csv(self.csv_path)
            # Normalizar tipos y valores
            df["es_fin_de_semana"] = df["es_fin_de_semana"].astype(bool)
            df["es_feriado"] = df["es_feriado"].astype(bool)
            df["temperatura_c"] = pd.to_numeric(df["temperatura_c"], errors="coerce").fillna(24.0)
            df["probabilidad_lluvia_pct"] = pd.to_numeric(
                df["probabilidad_lluvia_pct"], errors="coerce"
            ).fillna(0.0)
            df["cantidad_visitantes"] = pd.to_numeric(
                df["cantidad_visitantes"], errors="coerce"
            ).fillna(150).astype(int)
            df["clima_estado"] = df["clima_estado"].str.lower().str.strip()
            df["dia_semana"] = df["dia_semana"].str.lower().str.strip()

            # Asignar índice identificador 1..N
            df["id"] = range(1, len(df) + 1)
            self._df = df
            logger.info(f"Cargados {len(df)} registros históricos desde {self.csv_path}")
        except Exception as e:
            logger.error(f"Error cargando archivo {self.csv_path}: {e}")
            raise e

    @property
    def dataframe(self) -> pd.DataFrame:
        if self._df is None:
            self._cargar_datos()
        return self._df

    def obtener_todos(self, filtro: FiltroVisitas) -> RespuestaHistorico:
        """Obtiene registros con paginación y filtros opcionales."""
        df = self.dataframe.copy()

        if filtro.fecha_inicio:
            df = df[df["fecha"] >= filtro.fecha_inicio]
        if filtro.fecha_fin:
            df = df[df["fecha"] <= filtro.fecha_fin]
        if filtro.clima_estado:
            df = df[df["clima_estado"] == filtro.clima_estado.lower().strip()]
        if filtro.es_fin_de_semana is not None:
            df = df[df["es_fin_de_semana"] == filtro.es_fin_de_semana]
        if filtro.es_feriado is not None:
            df = df[df["es_feriado"] == filtro.es_feriado]

        total = len(df)
        paginated_df = df.iloc[filtro.offset : filtro.offset + filtro.limit]

        registros = [
            VisitaRegistro(
                id=int(row["id"]),
                fecha=str(row["fecha"]),
                dia_semana=str(row["dia_semana"]),
                es_fin_de_semana=bool(row["es_fin_de_semana"]),
                es_feriado=bool(row["es_feriado"]),
                clima_estado=str(row["clima_estado"]),
                temperatura_c=float(row["temperatura_c"]),
                probabilidad_lluvia_pct=float(row["probabilidad_lluvia_pct"]),
                cantidad_visitantes=int(row["cantidad_visitantes"]),
                zona=str(row.get("zona", self.settings.remanzo_azul_nombre)),
            )
            for _, row in paginated_df.iterrows()
        ]

        return RespuestaHistorico(
            total=total,
            limit=filtro.limit,
            offset=filtro.offset,
            registros=registros,
        )

    def obtener_similares(
        self,
        clima_estado: str,
        es_fin_de_semana: bool,
        es_feriado: bool = False,
        temperatura_c: float = 25.0,
        probabilidad_lluvia_pct: float = 10.0,
        dia_semana: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Busca registros históricos que presenten condiciones similares al día objetivo."""
        df = self.dataframe.copy()
        if df.empty:
            return []

        # 1. Filtro estricto inicial por tipo de día (fin de semana o feriado)
        mask_tipo_dia = (df["es_fin_de_semana"] == es_fin_de_semana) | (df["es_feriado"] == es_feriado)
        sub_df = df[mask_tipo_dia].copy()

        # Si el subconjunto es muy pequeño, considerar todo el dataframe
        if len(sub_df) < 10:
            sub_df = df.copy()

        # 2. Calcular distancia / similitud ponderada
        # Penalización por diferencia de clima
        clima_norm = clima_estado.lower().strip()
        clima_penalty = np.where(sub_df["clima_estado"] == clima_norm, 0.0, 2.5)

        # Penalización por día de semana si se conoce
        dia_penalty = 0.0
        if dia_semana:
            dia_penalty = np.where(sub_df["dia_semana"] == dia_semana.lower().strip(), -0.5, 0.5)

        # Distancia normalizada en temperatura y lluvia
        temp_dist = np.abs(sub_df["temperatura_c"] - temperatura_c) / 5.0
        lluvia_dist = np.abs(sub_df["probabilidad_lluvia_pct"] - probabilidad_lluvia_pct) / 25.0

        # Score de distancia total (menor es mejor)
        distancia = clima_penalty + dia_penalty + temp_dist + lluvia_dist
        sub_df["distancia"] = distancia

        top_df = sub_df.sort_values(by="distancia", ascending=True).head(limit)
        return top_df.to_dict(orient="records")

    def obtener_estadisticas(self) -> EstadisticasVisitas:
        """Calcula agregaciones y estadísticas globales sobre el histórico de visitas."""
        df = self.dataframe
        if df.empty:
            return EstadisticasVisitas(
                total_registros=0,
                fecha_minima="",
                fecha_maxima="",
                promedio_visitantes=0.0,
                mediana_visitantes=0.0,
                min_visitantes=0,
                max_visitantes=0,
                desviacion_estandar=0.0,
                promedio_fin_de_semana=0.0,
                promedio_dia_semana=0.0,
                promedio_feriados=0.0,
                promedio_por_clima={},
                promedio_por_dia_semana={},
                distribucion_clima={},
            )

        promedio_fin_de_semana = float(df[df["es_fin_de_semana"]]["cantidad_visitantes"].mean())
        promedio_dia_semana = float(df[~df["es_fin_de_semana"]]["cantidad_visitantes"].mean())
        feriados_series = df[df["es_feriado"]]["cantidad_visitantes"]
        promedio_feriados = float(feriados_series.mean()) if not feriados_series.empty else promedio_fin_de_semana

        prom_clima = {
            k: round(float(v), 1)
            for k, v in df.groupby("clima_estado")["cantidad_visitantes"].mean().items()
        }
        prom_dia = {
            k: round(float(v), 1)
            for k, v in df.groupby("dia_semana")["cantidad_visitantes"].mean().items()
        }
        dist_clima = {str(k): int(v) for k, v in df["clima_estado"].value_counts().items()}

        return EstadisticasVisitas(
            total_registros=len(df),
            fecha_minima=str(df["fecha"].min()),
            fecha_maxima=str(df["fecha"].max()),
            promedio_visitantes=round(float(df["cantidad_visitantes"].mean()), 1),
            mediana_visitantes=round(float(df["cantidad_visitantes"].median()), 1),
            min_visitantes=int(df["cantidad_visitantes"].min()),
            max_visitantes=int(df["cantidad_visitantes"].max()),
            desviacion_estandar=round(float(df["cantidad_visitantes"].std()), 1),
            promedio_fin_de_semana=round(promedio_fin_de_semana, 1),
            promedio_dia_semana=round(promedio_dia_semana, 1),
            promedio_feriados=round(promedio_feriados, 1),
            promedio_por_clima=prom_clima,
            promedio_por_dia_semana=prom_dia,
            distribucion_clima=dist_clima,
        )
