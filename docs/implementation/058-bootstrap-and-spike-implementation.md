# Bootstrap y spike — Implementación inicial

## Estado

- Bloque 0 — Bootstrap: **implementado y verificado localmente**.
- Bloque 1 — Spike Qwen: **código implementado; ejecución live pendiente de API key**.
- Fecha: 2026-07-10.

## Archivos implementados

- FastAPI con health endpoints;
- configuración Pydantic Settings;
- logs JSON;
- cliente Qwen tipado;
- normalización de tool calls;
- JSON Object mode con validación Pydantic;
- manejo seguro de errores;
- Dockerfile;
- Docker Compose;
- Makefile;
- CI de GitHub;
- pruebas unitarias;
- scripts S-01 a S-06;
- plantilla de resultados del spike.

## Decisiones aplicadas

- `qwen3.7-plus` como modelo principal;
- `qwen3.6-flash` como fallback;
- OpenAI-compatible Chat Completions;
- thinking desactivado;
- sin `max_tokens` en JSON mode;
- aplicación arranca sin API key;
- no se imprime ni persiste el secreto;
- tests live excluidos del CI normal.

## Verificación requerida para cerrar el gate

El propietario del proyecto debe configurar una clave Qwen Cloud y ejecutar:

```bash
cp .env.example .env
# Añadir DASHSCOPE_API_KEY al archivo local .env o exportarla en la shell.
make qwen-spike
```

Después se actualiza `scripts/qwen_spike/results.md` con resultados reales y se toma la decisión go/no-go.

## Limitación consciente

No se ha implementado todavía catálogo persistente, tools de dominio, orquestador ni endpoints de inquiries. Hacerlo antes de ejecutar el spike contradiría el gate aprobado.

## Evidencia local

- `ruff check`: aprobado.
- `mypy` en modo estricto: aprobado para 12 archivos fuente.
- `pytest`: 10 pruebas aprobadas.
- cobertura: 87 %.
- prueba local de clave ausente: error seguro `QWEN_NOT_CONFIGURED`.
- Dockerfile: generado, no construido en este entorno porque Docker no está disponible.
- spike live: no ejecutado porque no se proporcionó una API key.
