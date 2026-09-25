import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.config.settings import get_settings
from src.api.routes import router as api_router

settings = get_settings()

app = FastAPI(
    title=f"{settings.app_name} — API de Predicción de Afluencia",
    description=(
        "Sistema inteligente de predicción de afluencia turística para **El Remanzo Azul**, "
        "integrado con microservicio meteorológico y patrones históricos de visitantes."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de negocio tanto en raíz como en prefijo /api/v1
app.include_router(api_router, tags=["PrediRemanzoAzul"])
app.include_router(api_router, prefix="/api/v1", tags=["API v1"])


@app.get("/health", tags=["Salud y Monitoreo"])
async def health_check():
    """Endpoint de comprobación de salud para monitoreo, balanceadores y EC2."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "remanzo_azul": {
            "nombre": settings.remanzo_azul_nombre,
            "coordenadas": {
                "latitude": settings.remanzo_azul_latitude,
                "longitude": settings.remanzo_azul_longitude,
            },
        },
    }


# Montar archivos estáticos para la interfaz web interactiva
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse(
            {
                "mensaje": f"Bienvenido a {settings.app_name}",
                "documentacion": "/docs",
                "prediccion_hoy": "/prediccion/hoy",
                "clima_actual": "/clima/actual",
            }
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
