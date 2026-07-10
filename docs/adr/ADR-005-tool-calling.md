# ADR-005: Estrategia de tool calling

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

El agente debe ejecutar herramientas sin permitir acciones arbitrarias ni bucles indefinidos.

## Decisión

Implementar un ciclo de function calling controlado por el backend, con registro de tools, JSON Schema, validación Pydantic, allowlist, máximo de 6 rondas y 10 ejecuciones. Las tools de escritura interna requieren validación e idempotencia.

## Alternativas consideradas

- **ReAct abierto:** flexible, pero poco predecible.
- **Flujo totalmente determinista:** robusto, pero demuestra menos autonomía.
- **MCP:** útil para tools remotas reutilizables, innecesario para funciones locales del MVP.

## Consecuencias

**Positivas:** equilibrio entre autonomía y control.  
**Negativas:** requiere código de orquestación.  
**Riesgo:** el modelo puede omitir tools; el orquestador puede exigir fases obligatorias.

## Condición de revisión

Revisar MCP cuando existan integraciones externas reales o tools compartidas entre aplicaciones.
