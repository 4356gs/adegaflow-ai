# AdegaFlow AI API

Bootstrap técnico del backend FastAPI y adaptador Qwen Cloud.

## Requisitos

- Python 3.12+
- una API key de Qwen Cloud para ejecutar pruebas live

## Instalación

Desde la raíz:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./apps/api[dev]"
cp .env.example .env
```

## Ejecución

```bash
make run-api
```

Endpoints:

- `GET /health`
- `GET /api/v1/health`
- OpenAPI: `/docs`

## Calidad

```bash
make check-api
```

## Qwen Cloud

El cliente utiliza el endpoint OpenAI-compatible configurado mediante:

- `DASHSCOPE_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_MODEL`
- `QWEN_FALLBACK_MODEL`
- `QWEN_TIMEOUT_SECONDS`

La aplicación puede arrancar sin clave. Los endpoints informan `qwen_configured=false`; las llamadas al proveedor fallan con un error tipado y seguro.
