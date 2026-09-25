from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación PrediRemanzoAzul."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Identificación
    app_name: str = Field(default="PrediRemanzoAzul", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: Union[List[str], str] = Field(default=["*"], alias="CORS_ORIGINS")

    # Coordenadas y Parámetros del destino turístico Remanzo Azul
    remanzo_azul_nombre: str = Field(default="Remanzo Azul", alias="REMANZO_AZUL_NOMBRE")
    remanzo_azul_latitude: float = Field(default=6.2975, alias="REMANZO_AZUL_LATITUDE")
    remanzo_azul_longitude: float = Field(default=-75.0350, alias="REMANZO_AZUL_LONGITUDE")
    remanzo_azul_timezone: str = Field(default="America/Bogota", alias="REMANZO_AZUL_TIMEZONE")

    # API de Clima Principal (D:\Proyecto_Climatico)
    weather_api_base_url: str = Field(
        default="http://127.0.0.1:8000/api/v1", alias="WEATHER_API_BASE_URL"
    )
    weather_api_timeout_seconds: float = Field(
        default=4.0, alias="WEATHER_API_TIMEOUT_SECONDS"
    )

    # Resiliencia: Fallback a Open-Meteo directo si la API local no está disponible
    fallback_open_meteo_enabled: bool = Field(
        default=True, alias="FALLBACK_OPEN_METEO_ENABLED"
    )
    open_meteo_base_url: str = Field(
        default="https://api.open-meteo.com/v1", alias="OPEN_METEO_BASE_URL"
    )

    # Archivo de histórico de visitas
    historico_csv_path: str = Field(
        default="data/historico_visitas_remanzo_azul.csv", alias="HISTORICO_CSV_PATH"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def resolve_csv_path(self) -> Path:
        """Resuelve la ruta al CSV de visitas históricas con múltiples fallbacks."""
        candidate = Path(self.historico_csv_path)
        if candidate.exists():
            return candidate

        # Intentar en data/ o DatosHistoricos/
        fallback_candidates = [
            Path("data/historico_visitas_remanzo_azul.csv"),
            Path("DatosHistoricos/historico_visitas_remanzo_azul.csv"),
            Path("../DatosHistoricos/historico_visitas_remanzo_azul.csv"),
            Path("D:/PediccionRemanzoAzul/DatosHistoricos/historico_visitas_remanzo_azul.csv"),
        ]
        for fb in fallback_candidates:
            if fb.exists():
                return fb
        return candidate


@lru_cache()
def get_settings() -> Settings:
    return Settings()
