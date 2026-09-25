# PrediRemanzoAzul 🌊🏖️

> **Sistema Inteligente de Predicción de Afluencia Turística para "El Remanzo Azul"**  
> Cruzando meteorología en tiempo real, patrones históricos y modelos de predicción contextual.

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13%20%7C%203.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![AWS EC2](https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazon-aws&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-18%20Passed-success)

---

## 1. Resumen del Proyecto

**PrediRemanzoAzul** es un software desarrollado como un proyecto y repositorio independiente cuyo objetivo primordial es predecir cuántas personas visitarán **hoy** la zona turística **Remanzo Azul** (acotado exclusivamente a este destino).

Para lograrlo, el sistema integra:
1. **API de Clima en tiempo real:** Consume prioritariamente el microservicio meteorológico existente (`D:\Proyecto_Climatico`), con un mecanismo de conmutación por error (*failover*) resiliente hacia Open-Meteo para garantizar 100% de disponibilidad.
2. **Base de Datos Histórica:** 1,096 registros de visitas recopilados entre 2023 y 2025 (`data/historico_visitas_remanzo_azul.csv`).
3. **Motor Analítico de Predicción:** Algoritmo ponderado por k-vecinos en espacio meteorológico-temporal (clima, temperatura, precipitación, fin de semana, festivos), calculando visitantes estimados, intervalos de confianza y factores explicativos clave.
4. **Dashboard Web Interactivo y API REST:** Panel visual de control con glassmorphism, simulador "What-If" en tiempo real y documentación interactiva Swagger/OpenAPI.
5. **Infraestructura Cloud:** Despliegue en **AWS EC2** con pipeline automatizado de Integración y Despliegue Continuo (CI/CD) vía **GitHub Actions**.

---

## 2. Arquitectura de la Solución

```
┌─────────────────────────────────┐        ┌──────────────────────────────────────────────┐
│  Microservicio API-Clima        │        │        PrediRemanzoAzul                      │
│  (ProyectoClimatico existente)  │        │        (Nuevo software)                      │
│                                 │◄──────►│                                              │
│  - /weather/current             │  HTTP  │  - src/clima (Cliente HTTP con failover)     │
│  - /weather/hourly              │        │  - src/datos (Repositorio desacoplado)       │
│  - /weather/daily               │        │  - src/prediccion (Motor analítico)          │
└─────────────────────────────────┘        │  - src/api (Endpoints REST FastAPI)         │
                 ▲                         │  - static/ (Dashboard Web UI interactivo)    │
                 │ (Fallback si inactiva)   └──────────────────────┬───────────────────────┘
┌────────────────┴────────────────┐                               │
│  Open-Meteo Direct Failover     │                               ▼
│  (Alta Disponibilidad Cloud)    │                ┌──────────────────────────────┐
└─────────────────────────────────┘                │  Clientes / Usuarios         │
                                                   │  - "¿Cuántos vienen hoy?"    │
                                                   │  - "¿Cómo estará el clima?"  │
                                                   │  - Simulador What-If         │
                                                   └──────────────────────────────┘
```

---

## 3. Estructura del Repositorio

```
PrediRemanzoAzul/
├── .github/
│   └── workflows/
│       └── deploy.yml            # Pipeline de CI/CD para GitHub Actions
├── data/
│   └── historico_visitas_remanzo_azul.csv  # 1,096 registros históricos de visitas
├── deploy/
│   ├── nginx_prediremanzoazul.conf        # Configuración Reverse Proxy Nginx
│   ├── prediremanzoazul.service          # Servicio systemd Linux
│   └── setup_ec2.sh                      # Script de aprovisionamiento para EC2
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py             # Endpoints REST (predicción, clima, histórico)
│   ├── clima/
│   │   ├── __init__.py
│   │   ├── client.py             # Cliente HTTP con resiliencia y failover
│   │   └── models.py             # Modelos de dominio y mapeo de códigos WMO
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # Configuración Pydantic Settings (.env)
│   ├── datos/
│   │   ├── __init__.py
│   │   ├── models.py             # Esquemas de registros y filtros
│   │   └── repository.py         # Capa de datos desacoplada y agregaciones
│   ├── prediccion/
│   │   ├── __init__.py
│   │   ├── engine.py             # Motor de cálculo y k-vecinos contextuales
│   │   └── models.py             # Modelos de respuesta y simulación
│   └── main.py                   # Punto de entrada FastAPI y montaje estático
├── static/
│   └── index.html                # Dashboard Web moderno (Vanilla CSS / JS / Chart.js)
├── tests/
│   ├── test_api.py               # Pruebas de integración HTTP
│   ├── test_clima.py             # Pruebas del cliente meteorológico y fallbacks
│   ├── test_datos.py             # Pruebas del repositorio de visitas
│   └── test_prediccion.py        # Pruebas del motor predictivo
├── compose.yml                   # Orquestación Docker Compose
├── Dockerfile                    # Contenedor multi-stage optimizado
├── requirements.txt              # Dependencias de producción y testing
├── .env.example                  # Plantilla de variables de entorno
└── README.md                     # Documentación técnica completa
```

---

## 4. Endpoints Principales de la API

La aplicación expone una API REST moderna con documentación interactiva disponible en `/docs` (Swagger UI) y `/redoc`:

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/prediccion/hoy` | **Endpoint principal:** Predice visitantes estimados para hoy en Remanzo Azul. |
| `GET` | `/prediccion/fecha?fecha=YYYY-MM-DD` | Predicción de afluencia para una fecha futura o específica. |
| `POST` | `/prediccion/simulacion` | Simulador interactivo "What-If" variando clima y tipo de día. |
| `GET` | `/clima/actual` | Consulta meteorológica actual de Remanzo Azul. |
| `GET` | `/clima/horario?hours=24` | Pronóstico horario hora a hora. |
| `GET` | `/clima/proximos-dias?days=7`| Pronóstico meteorológico extendido día a día. |
| `GET` | `/clima/overview` | Resumen meteorológico consolidado (actual + horas + días). |
| `GET` | `/clima/estado-api` | Monitoreo de latencia y estado de la API de clima. |
| `GET` | `/historico` | Consulta paginada y filtrable del histórico de visitas. |
| `GET` | `/historico/estadisticas` | Métricas agregadas (promedio fin de semana, por clima, etc.). |
| `GET` | `/health` | Healthcheck para balanceadores de carga y monitoreo. |
| `GET` | `/` | Dashboard Web interactivo con gráficos y controles en tiempo real. |

### Ejemplo de Respuesta: `GET /prediccion/hoy`

```json
{
  "zona": "Remanzo Azul",
  "fecha": "2026-09-25",
  "dia_semana": "viernes",
  "es_fin_de_semana": false,
  "es_feriado": false,
  "clima_estimado": {
    "estado": "soleado",
    "temperatura": 27.5,
    "probabilidad_lluvia_pct": 10.0,
    "descripcion": "Soleado",
    "fuente_clima": "API-Clima (ProyectoClimatico)"
  },
  "visitantes_estimados": 248,
  "rango_estimado": {
    "min": 195,
    "max": 285
  },
  "nivel_afluencia": "Moderada",
  "confianza": "alta",
  "factores_clave": [
    "Día laboral: flujo de visitantes más moderado y enfocado en turismo local.",
    "Cielo despejado/soleado: condición óptima para disfrute de aguas, senderos y zonas recreativas.",
    "Baja probabilidad de lluvia (10.0%): estabilidad garantizada para actividades al aire libre."
  ],
  "fuente_datos": "simulada",
  "referencias_historicas_muestra": [ ... ],
  "nota": "Basado en datos históricos simulados y meteorología de Remanzo Azul"
}
```

---

## 5. Ejecución Local

### Opción A: Con Python (Recomendado para desarrollo)

1. **Clonar e ingresar al repositorio:**
   ```bash
   cd D:\PediccionRemanzoAzul
   ```

2. **Crear y activar entorno virtual:**
   ```bash
   python -m venv .venv
   # En Windows:
   .venv\Scripts\activate
   # En Linux / macOS:
   source .venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copiar archivo de variables de entorno:**
   ```bash
   copy .env.example .env   # En Linux: cp .env.example .env
   ```

5. **Iniciar el servidor:**
   ```bash
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
   ```

6. **Abrir en el navegador:**
   - **Dashboard Web:** [http://localhost:8080](http://localhost:8080)
   - **Documentación Swagger:** [http://localhost:8080/docs](http://localhost:8080/docs)
   - **Healthcheck:** [http://localhost:8080/health](http://localhost:8080/health)

---

### Opción B: Con Docker Compose

```bash
docker compose up --build -d
```

Para verificar logs:
```bash
docker compose logs -f
```

---

## 6. Pruebas Automatizadas

El proyecto cuenta con 18 pruebas unitarias y de integración:

```bash
# Ejecutar todas las pruebas
python -m pytest tests/ -v

# Ejecutar con reporte de cobertura de código
python -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## 7. Despliegue en AWS EC2 y CI/CD con GitHub Actions

### 7.1 Configuración de la Instancia EC2

1. **Crear Instancia:**
   - Tipo de AMI: **Ubuntu Server 24.04 LTS** o **22.04 LTS** (o Amazon Linux 2023).
   - Tipo de Instancia: `t3.micro` o `t3.small`.
   - Security Group (Puertos requeridos):
     - `22` (SSH): Restringido a tu IP.
     - `80` (HTTP): Abierto a `0.0.0.0/0`.
     - `443` (HTTPS): Abierto a `0.0.0.0/0`.
     - `8080` (Opcional si se accede directamente sin proxy Nginx).

2. **Aprovisionar el servidor:**
   Conéctate a la instancia por SSH y ejecuta el script automatizado:
   ```bash
   ssh -i /ruta/a/tu-llave.pem ubuntu@<IP_PUBLICA_EC2>
   curl -fsSL https://raw.githubusercontent.com/<TU_USUARIO>/PrediRemanzoAzul/main/deploy/setup_ec2.sh | bash
   ```

### 7.2 Configuración de Secretos en GitHub

En el repositorio de GitHub, ve a **Settings** > **Secrets and variables** > **Actions** y añade:

| Secreto | Descripción | Ejemplo |
|---|---|---|
| `EC2_HOST` | IP pública o DNS IPv4 de la instancia EC2 | `54.210.88.12` |
| `EC2_USER` | Usuario SSH del servidor | `ubuntu` (o `ec2-user`) |
| `EC2_SSH_KEY` | Contenido completo de tu archivo `.pem` | `-----BEGIN RSA PRIVATE KEY-----...` |
| `EC2_PORT` | Puerto SSH (opcional, por defecto 22) | `22` |

### 7.3 Flujo del Pipeline CI/CD

Cada vez que se realiza un `push` o `merge` a la rama `main`:
1. **Job Test:** Se instala Python 3.12, se instalan dependencias y se corren los 18 tests con reporte de cobertura.
2. **Job Deploy:** Si los tests son exitosos, se conecta por SSH a la máquina EC2, sincroniza el código fuente, reconstruye los contenedores Docker y verifica automáticamente el endpoint `/health`.
