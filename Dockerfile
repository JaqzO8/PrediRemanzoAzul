# Dockerfile para PrediRemanzoAzul
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Imagen final ligera y segura
FROM python:3.12-slim AS runner

WORKDIR /app

# Crear usuario sin privilegios para ejecución segura
RUN useradd -m -u 1001 appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser static/ /app/static/
COPY --chown=appuser:appuser data/ /app/data/
COPY --chown=appuser:appuser DatosHistoricos/ /app/DatosHistoricos/
COPY --chown=appuser:appuser .env.example /app/.env

USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
