# Especificación Técnica (Spec)
## Proyecto: PrediRemanzoAzul — Predicción de Afluencia Turística y climática para "El Remanzo Azul"

---

## 1. Resumen Ejecutivo

**PrediRemanzoAzul** es un nuevo software, alojado en su propio repositorio, cuyo objetivo es predecir cuántas personas visitarán **hoy** la zona turística **Remanzo Azul** (exclusivamente ese lugar, sin cubrir otros destinos). Para lograrlo, el sistema combinará:

- Datos de clima obtenidos desde la **API de clima ya existente** en la siguiente ruta de proyecto: D:\Proyecto_Climatico.
- Utiliza los datos históricos/simulados de visitas al Remanzo Azul en D:\PediccionRemanzoAzul\DatosHistoricos\historico_visitas_remanzo_azul.csv.
- Un modelo/lógica de predicción que cruce clima + histórico de afluencia para estimar la cantidad de visitantes del día.

El sistema se desplegará en **AWS**, usando **EC2** como servidor de aplicación y **GitHub Actions** para automatizar el despliegue (CI/CD).

---

## 2. Objetivos

### 2.1 Objetivo general
Disponer de un servicio que, al ser consultado, indique la afluencia estimada de visitantes al Remanzo Azul para el día actual (y opcionalmente otros momentos), apoyándose en datos climáticos y de comportamiento histórico.

### 2.2 Objetivos específicos
- Garantizar que la API de clima existente esté funcionando correctamente y sea consumida como servicio externo/interno.
- Crear el repositorio **PrediRemanzoAzul** como proyecto independiente.
- Simular o integrar una fuente de datos de visitas históricas al Remanzo Azul.
- Permitir que el usuario consulte el clima en **distintos momentos del tiempo** (hoy, horas específicas, próximos días si la API de clima lo permite).
- Calcular y mostrar una **predicción de visitas** para el día actual, acotada únicamente al Remanzo Azul.
- Desplegar la solución en AWS (EC2) con un pipeline automatizado vía GitHub Actions.

### 2.3 Fuera de alcance
- Predicción de afluencia para otras zonas turísticas distintas al Remanzo Azul.
- Predicciones a largo plazo (más allá del horizonte que permita la API de clima).
- Sistema de pagos, reservas o gestión de visitantes en sitio.

---

## 3. Arquitectura General

El sistema se compone de **dos repositorios independientes** que se comunican entre sí:

```
┌─────────────────────────────┐        ┌──────────────────────────────────┐
│   Repositorio: API-Clima    │        │   Repositorio: PrediRemanzoAzul   │
│  (ya existente, en uso)     │        │        (nuevo software)           │
│                              │◄──────►│                                    │
│  - Expone endpoints de clima│  HTTP  │  - Consume API de clima            │
│  - Clima actual / por hora  │        │  - Consulta datos simulados/BD     │
│  - Clima por fecha/rango    │        │    de visitas históricas           │
└─────────────────────────────┘        │  - Modelo de predicción de visitas │
                                        │  - Expone su propia API            │
                                        └──────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌──────────────────────────────────┐
                                        │     Usuario / Frontend / Cliente  │
                                        │  Consulta: "¿cuánta gente va a    │
                                        │   venir hoy al Remanzo Azul?"     │
                                        │  Consulta: "¿cómo estará el clima │
                                        │   en tal horario/fecha?"          │
                                        └──────────────────────────────────┘
```

### 3.1 Componentes principales
1. **API de Clima** (repositorio ya existente): debe validarse y asegurarse su correcto funcionamiento antes de integrarla.
2. **PrediRemanzoAzul** (nuevo repositorio):
   - Módulo de consumo de la API de clima.
   - Módulo de datos simulados/históricos de visitas.
   - Módulo/motor de predicción.
   - API propia (endpoints REST) para exponer resultados.
3. **Infraestructura AWS**: EC2 para hosting, con despliegue automatizado.
4. **GitHub Actions**: pipeline de CI/CD para el despliegue automático a AWS.

---

## 4. Fuentes de Datos

### 4.1 Datos de clima
- Se usará la **API de clima ya existente** (repositorio propio) como fuente principal.
- Si dicha API no cubre algún requerimiento (por ejemplo, pronósticos horarios extendidos), se evaluará el consumo de una **API externa de clima ya existente en el mercado** (ej. OpenWeatherMap, WeatherAPI, u otra) como fuente complementaria o de respaldo.
- El sistema debe permitir que el usuario consulte el clima en **distintos momentos**: clima actual, clima en una hora específica del día, y clima en fechas próximas (según lo que la API disponible permita).

### 4.2 Datos de visitas al Remanzo Azul
Dado que no existe (o no se menciona) un histórico real de visitantes, se plantea:
- **Opción A — Base de datos simulada:** crear un dataset sintético con registros históricos de visitas (fecha, hora, clima de ese día, cantidad de visitantes), generado con reglas realistas (ej. más visitantes en días soleados/fines de semana, menos en días lluviosos).
- **Opción B — Fuente real si existe:** si en el futuro existe una API o sistema de conteo real de visitantes, el módulo de datos debe poder sustituirse sin afectar el resto del sistema (diseño desacoplado).

**Estructura sugerida de la tabla/colección de visitas simuladas:**

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID / int | Identificador único del registro |
| `fecha` | date | Fecha del registro histórico |
| `hora` | time (opcional) | Franja horaria, si se maneja granularidad horaria |
| `clima_estado` | string | Ej. soleado, nublado, lluvioso, tormenta |
| `temperatura` | float | Temperatura registrada ese día/hora |
| `es_fin_de_semana` | boolean | Indicador de fin de semana o feriado |
| `cantidad_visitantes` | int | Número de visitantes registrados/simulados |

---

## 5. Funcionalidades del Sistema

### 5.1 Consulta de clima
- Endpoint para consultar el clima **actual** del Remanzo Azul.
- Endpoint para consultar el clima en un **momento específico** solicitado por el usuario (hora del día, fecha futura dentro del rango soportado).
- Manejo de errores si la API de clima no responde (uso de datos en caché o mensaje claro al usuario).

### 5.2 Predicción de visitas
- Endpoint principal: `GET /prediccion/hoy` → devuelve la cantidad estimada de visitantes para el día actual en el Remanzo Azul.
- El cálculo debe considerar como mínimo:
  - Clima del día (obtenido de la API de clima).
  - Patrón histórico/simulado de visitas en condiciones similares (mismo tipo de clima, mismo día de la semana, temporada).
- Respuesta de ejemplo (JSON):

```json
{
  "zona": "Remanzo Azul",
  "fecha": "2026-09-25",
  "clima_estimado": {
    "estado": "soleado",
    "temperatura": 27.5
  },
  "visitantes_estimados": 340,
  "confianza": "media",
  "fuente_datos": "simulada"
}
```

### 5.3 Consulta de datos históricos
- Endpoint para ver el histórico simulado usado como base del modelo (útil para trazabilidad y validación).

---

## 6. Diseño Técnico

### 6.1 Repositorio `PrediRemanzoAzul` — estructura sugerida
```
PrediRemanzoAzul/
├── src/
│   ├── clima/            # Módulo de consumo de la API de clima
│   ├── datos/            # Módulo de datos simulados / histórico de visitas
│   ├── prediccion/        # Lógica/modelo de predicción
│   ├── api/               # Endpoints REST expuestos por el sistema
│   └── config/             # Configuración (variables de entorno, conexión a BD, etc.)
├── tests/                  # Pruebas unitarias e integración
├── data/                   # Dataset simulado (si se usa archivo en vez de BD)
├── .github/
│   └── workflows/
│       └── deploy.yml      # Pipeline de GitHub Actions
├── Dockerfile               # (opcional) contenedorización para despliegue en EC2
├── requirements.txt / package.json
└── README.md
```

### 6.2 Base de datos
- Motor sugerido: base de datos relacional (PostgreSQL/MySQL) o, si se prioriza simplicidad, un almacenamiento simple (SQLite/JSON) para los datos simulados en una primera fase.
- La capa de acceso a datos debe estar desacoplada del motor de predicción, de forma que cambiar la fuente de datos (simulada → real) no requiera reescribir la lógica de negocio.

### 6.3 Motor de predicción
- Primera versión: modelo basado en reglas/promedios históricos filtrados por condición climática y tipo de día (regla simple o modelo estadístico ligero).
- Versión futura (opcional): modelo de machine learning entrenado con datos reales una vez existan.

---

## 7. Infraestructura AWS

### 7.1 Servicios a utilizar
- **Amazon EC2**: instancia donde se ejecutará la aplicación (API de PrediRemanzoAzul).
- **Security Groups**: reglas de firewall para permitir tráfico HTTP/HTTPS (puertos 80/443) y SSH (puerto 22, restringido a IPs autorizadas).
- **(Opcional) RDS**: si se decide usar base de datos relacional gestionada en vez de alojarla en la propia instancia EC2.
- **(Opcional) IAM Roles**: para dar permisos controlados a la instancia EC2 y a GitHub Actions sin exponer credenciales sensibles.

### 7.2 Configuración de la instancia EC2
- Sistema operativo: Amazon Linux 2023 o Ubuntu Server LTS.
- Software requerido: runtime de la aplicación (Node.js/Python según se elija), servidor web/proxy (Nginx) como reverse proxy hacia la app.
- La aplicación debe ejecutarse como servicio persistente (systemd, PM2, o contenedor Docker) para sobrevivir a reinicios.

### 7.3 Conexión y seguridad
- Acceso SSH mediante llave (`.pem`) almacenada de forma segura, nunca en el repositorio.
- Credenciales de AWS (Access Key / Secret Key) almacenadas como **GitHub Secrets**, nunca en el código.
- Uso de HTTPS mediante certificado (Let's Encrypt o AWS Certificate Manager + Load Balancer si se escala a futuro).

---

## 8. Integración Continua y Despliegue (CI/CD con GitHub Actions)

### 8.1 Flujo del pipeline
1. **Trigger:** push o merge a la rama `main` del repositorio `PrediRemanzoAzul`.
2. **Build/Test:** instalación de dependencias y ejecución de pruebas automatizadas.
3. **Despliegue:** conexión por SSH a la instancia EC2 y actualización del código (pull + reinicio del servicio), o construcción y despliegue de una imagen Docker.

### 8.2 Esquema del workflow (referencia conceptual)
```yaml
name: Deploy to AWS EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout código
        uses: actions/checkout@v4

      - name: Instalar dependencias y ejecutar pruebas
        run: |
          # instalar dependencias
          # correr tests

      - name: Desplegar a EC2 vía SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /ruta/del/proyecto
            git pull origin main
            # instalar dependencias nuevas si aplica
            # reiniciar el servicio (systemctl restart / pm2 restart / docker compose up -d)
```

### 8.3 Secrets necesarios en GitHub
| Secret | Descripción |
|---|---|
| `EC2_HOST` | IP o DNS público de la instancia EC2 |
| `EC2_USER` | Usuario SSH (ej. `ubuntu`, `ec2-user`) |
| `EC2_SSH_KEY` | Llave privada SSH para autenticación |
| `AWS_ACCESS_KEY_ID` | (si se usan servicios adicionales de AWS vía CLI/SDK) |
| `AWS_SECRET_ACCESS_KEY` | (si se usan servicios adicionales de AWS vía CLI/SDK) |
| `WEATHER_API_URL` / `WEATHER_API_KEY` | Credenciales/endpoint de la API de clima existente |

---

## 9. Consideraciones de Validación

- Antes de integrar, verificar que la **API de clima** responda correctamente (pruebas de disponibilidad, formato de respuesta, manejo de errores/timeouts).
- Documentar claramente si se usan **datos simulados** en las respuestas de predicción, para que el usuario entienda que no son datos reales de conteo de personas (hasta que exista una fuente real).
- Contemplar límites de la API de clima externa (si se usa una de terceros): límites de peticiones por minuto/día, necesidad de API key, etc.

---

## 10. Roadmap Sugerido

1. **Fase 1:** Verificar y estabilizar la API de clima existente.
2. **Fase 2:** Crear el repositorio `PrediRemanzoAzul` con estructura base y datos simulados de visitas.
3. **Fase 3:** Implementar el motor de predicción (reglas simples basadas en clima + histórico).
4. **Fase 4:** Exponer la API propia con los endpoints de consulta de clima y predicción.
5. **Fase 5:** Configurar instancia EC2 en AWS y desplegar manualmente por primera vez.
6. **Fase 6:** Automatizar el despliegue con GitHub Actions (CI/CD).
7. **Fase 7 (futuro):** Sustituir datos simulados por datos reales de conteo de visitantes, si llegan a existir.

---

## 11. Glosario

- **Remanzo Azul:** zona turística específica, único lugar cubierto por este sistema de predicción.
- **API de clima:** servicio ya desarrollado que provee información meteorológica.
- **PrediRemanzoAzul:** nuevo repositorio/software encargado de predecir la afluencia de visitantes.
- **Datos simulados:** conjunto de datos sintéticos generados para representar un histórico de visitas, en ausencia de datos reales.
