# 🚌 Backend - Planificador de Rutas de Micros Santa Cruz

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)

Este repositorio contiene el código fuente del **Backend** para el Sistema de Información Geográfica (SIG) de transporte público en Santa Cruz de la Sierra. Provee una API RESTful de alto rendimiento para la gestión de rutas, planificación de viajes y administración de la red de transporte.

## 📂 Estructura del Proyecto

```
backend/
├── app/                # Código fuente de la aplicación
│   ├── api/            # Controladores / Endpoints
│   ├── core/           # Configuración y seguridad
│   ├── crud/           # Operaciones de Base de Datos
│   ├── models/         # Modelos SQLAlchemy
│   ├── schemas/        # Esquemas Pydantic (DTOs)
│   └── services/       # Lógica de Negocio
├── docs/               # Documentación detallada del proyecto
├── tests/              # Tests unitarios y de integración
├── Dockerfile          # Definición de imagen Docker
└── docker-compose.yml  # Orquestación de servicios
```

## 🚀 Inicio Rápido

La forma más sencilla de ejecutar el proyecto es utilizando Docker, pero también puedes ejecutarlo manualmente.

### Opción 1: Docker (Recomendado)

1.  **Clonar el repositorio**
2.  **Navegar al directorio:** `cd backend`
3.  **Ejecutar:**
    ```bash
    docker-compose up --build
    ```

La API estará disponible en `http://localhost:8000`.

### Opción 2: Ejecución Manual (Virtual Environment)

Si prefieres ejecutarlo localmente sin Docker, sigue estos pasos:

1.  **Crear un entorno virtual:**

    *   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   **Linux / macOS:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar variables de entorno:**
    Asegúrate de tener un archivo `.env` configurado. Puedes usar `.env.example` como base.

4.  **Ejecutar el servidor:**
    ```bash
    uvicorn app.main:app --reload
    ```

La API estará disponible en `http://localhost:8000`.

## 📚 Documentación

Para información detallada sobre la arquitectura, endpoints y guías de desarrollo, por favor consulta la carpeta `docs/`:

- [📄 Documentación Completa del Proyecto](docs/README.md)

## 🧪 Tests

Para ejecutar los tests automatizados:

```bash
docker-compose exec web pytest
```

## 👥 Autores

- **Equipo SIG - UAGRM**
- Facultad de Ciencias de la Computación
