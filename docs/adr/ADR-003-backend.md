# ADR-003: Backend con FastAPI

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

La API debe integrar modelos, validar JSON, ejecutar tools, persistir datos y exponer OpenAPI.

## Decisión

Usar FastAPI, Python, Pydantic, SQLAlchemy 2.0 y Alembic. No usar un framework de agentes en el núcleo; el orquestador será código de aplicación explícito.

## Alternativas consideradas

- **Node/NestJS:** coherencia de lenguaje, pero menor alineación con el trabajo IA previsto.
- **Django:** demasiada superficie para una API pequeña.
- **Qwen-Agent/LangChain:** aceleran patrones, pero añaden abstracción, dependencia y dificultad de depuración.

## Consecuencias

**Positivas:** validación fuerte, documentación automática, ecosistema IA.  
**Negativas:** mantener contratos entre TypeScript y Python.  
**Riesgo:** escribir infraestructura propia excesiva; se mitiga con un orquestador pequeño.

## Condición de revisión

Revisar un framework de agentes solo si resuelve un bloqueo demostrado en el spike.
