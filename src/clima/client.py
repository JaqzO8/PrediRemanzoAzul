import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx

from src.config.settings import Settings, get_settings
from src.clima.models import (
    ClimaActual,
    PronosticoHora,
    PronosticoDia,
    ClimaOverview,
    mapear_codigo_wmo,
)

logger = logging.getLogger(__name__)


class ClimaClient:
    """Cliente HTTP resiliente para obtener datos del clima del Remanzo Azul.

    Prioridad 1: API de Clima existente (D:\\Proyecto_Climatico en WEATHER_API_BASE_URL).
    Prioridad 2: Fallback directo a Open-Meteo API pública si el microservicio local no está corriendo.
    Prioridad 3: Modo seguro sintético basado en medias climáticas de la zona si no hay conectividad.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.weather_api_base_url.rstrip("/")
        self.timeout = self.settings.weather_api_timeout_seconds
        self.lat = self.settings.remanzo_azul_latitude
        self.lon = self.settings.remanzo_azul_longitude
        self.zona = self.settings.remanzo_azul_nombre

    async def get_current_weather(self) -> ClimaActual:
        """Obtiene el clima actual para Remanzo Azul."""
        # 1. Intentar API local existente
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/weather/current",
                    params={"latitude": self.lat, "longitude": self.lon},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current", {})
                    wmo_code = curr.get("weather_code", 0)
                    wmo_label = curr.get("weather_label", "")
                    estado = mapear_codigo_wmo(wmo_code, wmo_label)
                    temp = float(curr.get("temperature", 24.0))
                    precip = float(curr.get("precipitation", 0.0))
                    # Estimar probabilidad de lluvia a partir de precipitación si no viene explícita
                    prob_lluvia = min(100.0, max(0.0, precip * 20.0)) if precip > 0 else (15.0 if estado in ("nublado", "parcialmente nublado") else 5.0)

                    return ClimaActual(
                        zona=self.zona,
                        estado=estado,
                        temperatura_c=round(temp, 1),
                        probabilidad_lluvia_pct=round(prob_lluvia, 1),
                        humedad_relativa_pct=curr.get("relative_humidity"),
                        viento_kmh=curr.get("wind_speed"),
                        codigo_wmo=wmo_code,
                        descripcion=wmo_label or estado.capitalize(),
                        fuente="API-Clima (ProyectoClimatico)",
                        hora_observacion=data.get("observed_at", datetime.now().isoformat()),
                    )
        except Exception as e:
            logger.warning(
                f"API-Clima primaria no disponible ({self.base_url}): {e}. Conmutando a fallback..."
            )

        # 2. Intentar Fallback Open-Meteo directo
        if self.settings.fallback_open_meteo_enabled:
            try:
                return await self._fetch_open_meteo_current()
            except Exception as e:
                logger.warning(f"Fallback Open-Meteo falló: {e}. Activando modo sintético seguro.")

        # 3. Fallback Sintético Seguro
        return self._generar_clima_sintetico_seguro()

    async def get_hourly_forecast(self, hours: int = 24) -> List[PronosticoHora]:
        """Obtiene el pronóstico por horas para las próximas N horas."""
        hours = max(1, min(hours, 72))

        # 1. Intentar API local existente
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/weather/hourly",
                    params={"latitude": self.lat, "longitude": self.lon, "hours": hours},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    lista_horas = []
                    for item in data.get("hourly", []):
                        wmo = item.get("weather_code", 0)
                        lbl = item.get("weather_label", "")
                        lista_horas.append(
                            PronosticoHora(
                                hora=item.get("time", ""),
                                temperatura_c=round(float(item.get("temperature", 24.0)), 1),
                                probabilidad_lluvia_pct=round(
                                    float(item.get("precipitation_probability", 0)), 1
                                ),
                                estado=mapear_codigo_wmo(wmo, lbl),
                                descripcion=lbl or "Normal",
                                viento_kmh=item.get("wind_speed"),
                            )
                        )
                    if lista_horas:
                        return lista_horas
        except Exception as e:
            logger.warning(f"Error consultando pronóstico horario en API local: {e}")

        # 2. Intentar Fallback Open-Meteo
        try:
            return await self._fetch_open_meteo_hourly(hours)
        except Exception as e:
            logger.warning(f"Fallback horario Open-Meteo falló: {e}")
            return self._generar_horas_sinteticas(hours)

    async def get_daily_forecast(self, days: int = 7) -> List[PronosticoDia]:
        """Obtiene pronóstico diario para los próximos N días."""
        days = max(1, min(days, 14))

        # 1. Intentar API local
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/weather/daily",
                    params={"latitude": self.lat, "longitude": self.lon, "days": days},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    lista_dias = []
                    for item in data.get("daily", []):
                        wmo = item.get("weather_code", 0)
                        lbl = item.get("weather_label", "")
                        t_max = float(item.get("temperature_max", 26.0))
                        t_min = float(item.get("temperature_min", 18.0))
                        t_avg = round((t_max + t_min) / 2.0, 1)
                        lista_dias.append(
                            PronosticoDia(
                                fecha=item.get("date", ""),
                                temperatura_max_c=round(t_max, 1),
                                temperatura_min_c=round(t_min, 1),
                                temperatura_promedio_c=t_avg,
                                probabilidad_lluvia_pct=round(
                                    float(item.get("precipitation_probability_max", 0)), 1
                                ),
                                estado=mapear_codigo_wmo(wmo, lbl),
                                descripcion=lbl or "Estable",
                                viento_max_kmh=item.get("wind_speed_max"),
                            )
                        )
                    if lista_dias:
                        return lista_dias
        except Exception as e:
            logger.warning(f"Error consultando pronóstico diario en API local: {e}")

        # 2. Intentar Fallback Open-Meteo
        try:
            return await self._fetch_open_meteo_daily(days)
        except Exception as e:
            logger.warning(f"Fallback diario Open-Meteo falló: {e}")
            return self._generar_dias_sinteticos(days)

    async def get_weather_overview(self) -> ClimaOverview:
        """Obtiene el resumen consolidado de clima: actual, próximas 12 horas y próximos 5 días."""
        actual = await self.get_current_weather()
        horas = await self.get_hourly_forecast(hours=12)
        dias = await self.get_daily_forecast(days=5)

        return ClimaOverview(
            zona=self.zona,
            fuente=actual.fuente,
            actual=actual,
            proximas_horas=horas,
            proximos_dias=dias,
        )

    async def check_api_status(self) -> Dict[str, Any]:
        """Verifica la conectividad y estado de salud de la API meteorológica."""
        estado_primaria = "desconectada"
        latencia_ms = None
        info_extra = {}

        try:
            t0 = datetime.now()
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/weather/provider/status")
                latencia_ms = int((datetime.now() - t0).total_seconds() * 1000)
                if resp.status_code == 200:
                    estado_primaria = "operativa"
                    info_extra = resp.json()
        except Exception as e:
            estado_primaria = f"inactiva ({type(e).__name__})"

        return {
            "api_primaria_url": self.base_url,
            "api_primaria_estado": estado_primaria,
            "latencia_ms": latencia_ms,
            "fallback_open_meteo_activo": self.settings.fallback_open_meteo_enabled,
            "zona_monitoreada": self.zona,
            "coordenadas": {"lat": self.lat, "lon": self.lon},
            "proveedor_info": info_extra,
        }

    # -------------------------------------------------------------
    # Métodos privados de Fallback a Open-Meteo directo
    # -------------------------------------------------------------
    async def _fetch_open_meteo_current(self) -> ClimaActual:
        url = f"{self.settings.open_meteo_base_url}/forecast"
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": self.settings.remanzo_azul_timezone,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            curr = data.get("current", {})
            wmo_code = curr.get("weather_code", 0)
            estado = mapear_codigo_wmo(wmo_code)
            temp = float(curr.get("temperature_2m", 25.0))
            precip = float(curr.get("precipitation", 0.0))
            prob_lluvia = min(100.0, max(0.0, precip * 25.0)) if precip > 0 else (20.0 if "nublado" in estado else 5.0)

            return ClimaActual(
                zona=self.zona,
                estado=estado,
                temperatura_c=round(temp, 1),
                probabilidad_lluvia_pct=round(prob_lluvia, 1),
                humedad_relativa_pct=curr.get("relative_humidity_2m"),
                viento_kmh=curr.get("wind_speed_10m"),
                codigo_wmo=wmo_code,
                descripcion=estado.capitalize(),
                fuente="Open-Meteo Direct (Fallback Resiliente)",
                hora_observacion=curr.get("time", datetime.now().isoformat()),
            )

    async def _fetch_open_meteo_hourly(self, hours: int) -> List[PronosticoHora]:
        url = f"{self.settings.open_meteo_base_url}/forecast"
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
            "timezone": self.settings.remanzo_azul_timezone,
            "forecast_hours": hours,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])[:hours]
            temps = hourly.get("temperature_2m", [])[:hours]
            probs = hourly.get("precipitation_probability", [])[:hours]
            codes = hourly.get("weather_code", [])[:hours]
            winds = hourly.get("wind_speed_10m", [])[:hours]

            res = []
            for i, t in enumerate(times):
                wmo = codes[i] if i < len(codes) else 0
                est = mapear_codigo_wmo(wmo)
                res.append(
                    PronosticoHora(
                        hora=t,
                        temperatura_c=round(float(temps[i]), 1) if i < len(temps) else 24.0,
                        probabilidad_lluvia_pct=round(float(probs[i]), 1) if i < len(probs) else 0.0,
                        estado=est,
                        descripcion=est.capitalize(),
                        viento_kmh=round(float(winds[i]), 1) if i < len(winds) else 10.0,
                    )
                )
            return res

    async def _fetch_open_meteo_daily(self, days: int) -> List[PronosticoDia]:
        url = f"{self.settings.open_meteo_base_url}/forecast"
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
            "timezone": self.settings.remanzo_azul_timezone,
            "forecast_days": days,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])[:days]
            t_maxs = daily.get("temperature_2m_max", [])[:days]
            t_mins = daily.get("temperature_2m_min", [])[:days]
            probs = daily.get("precipitation_probability_max", [])[:days]
            codes = daily.get("weather_code", [])[:days]
            winds = daily.get("wind_speed_10m_max", [])[:days]

            res = []
            for i, d in enumerate(dates):
                wmo = codes[i] if i < len(codes) else 0
                est = mapear_codigo_wmo(wmo)
                max_t = float(t_maxs[i]) if i < len(t_maxs) else 28.0
                min_t = float(t_mins[i]) if i < len(t_mins) else 18.0
                res.append(
                    PronosticoDia(
                        fecha=d,
                        temperatura_max_c=round(max_t, 1),
                        temperatura_min_c=round(min_t, 1),
                        temperatura_promedio_c=round((max_t + min_t) / 2.0, 1),
                        probabilidad_lluvia_pct=round(float(probs[i]), 1) if i < len(probs) else 10.0,
                        estado=est,
                        descripcion=est.capitalize(),
                        viento_max_kmh=round(float(winds[i]), 1) if i < len(winds) else 12.0,
                    )
                )
            return res

    def _generar_clima_sintetico_seguro(self) -> ClimaActual:
        """Genera un estado climático realista y seguro para Remanzo Azul si todas las APIs fallan."""
        return ClimaActual(
            zona=self.zona,
            estado="soleado",
            temperatura_c=27.5,
            probabilidad_lluvia_pct=10.0,
            humedad_relativa_pct=65,
            viento_kmh=12.0,
            codigo_wmo=1,
            descripcion="Mayormente soleado (Modo Resiliencia)",
            fuente="Estimación Interna de Resiliencia",
            hora_observacion=datetime.now().isoformat(),
        )

    def _generar_horas_sinteticas(self, hours: int) -> List[PronosticoHora]:
        now = datetime.now()
        res = []
        for i in range(hours):
            h_time = now.replace(minute=0, second=0, microsecond=0)
            res.append(
                PronosticoHora(
                    hora=f"+{i}h ({h_time.hour + i % 24:02d}:00)",
                    temperatura_c=round(24.0 + (3.0 if 11 <= (h_time.hour + i) % 24 <= 16 else -2.0), 1),
                    probabilidad_lluvia_pct=15.0,
                    estado="parcialmente nublado",
                    descripcion="Parcialmente nublado",
                    viento_kmh=10.0,
                )
            )
        return res

    def _generar_dias_sinteticos(self, days: int) -> List[PronosticoDia]:
        from datetime import timedelta

        today = datetime.now().date()
        res = []
        for i in range(days):
            d = today + timedelta(days=i)
            res.append(
                PronosticoDia(
                    fecha=d.isoformat(),
                    temperatura_max_c=28.5,
                    temperatura_min_c=18.0,
                    temperatura_promedio_c=23.3,
                    probabilidad_lluvia_pct=20.0,
                    estado="soleado" if i % 2 == 0 else "parcialmente nublado",
                    descripcion="Agradable",
                    viento_max_kmh=14.0,
                )
            )
        return res
