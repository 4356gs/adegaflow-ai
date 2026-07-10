# ADR-004: Integración con Qwen Cloud

- **Estado:** Accepted for MVP — amended by ADR-011
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

Qwen Cloud debe ser central, verificable y compatible con tool calling y respuestas estructuradas.

## Decisión

Usar la API OpenAI-compatible de Qwen Cloud mediante el SDK OpenAI para Python. El endpoint, modelo y parámetros serán configurables. The API style remains OpenAI-compatible Chat Completions. Model defaults are amended by ADR-011. Se utilizará Chat Completions para el MVP.

## Alternativas consideradas

- **SDK DashScope nativo:** válido, pero reduce portabilidad y familiaridad.
- **Responses API:** ofrece herramientas avanzadas, pero no son necesarias para el flujo inicial.
- **Modelo local:** no cumple la centralidad de Qwen Cloud.

## Consecuencias

**Positivas:** integración simple, tool calling estándar, facilidad de pruebas.  
**Negativas:** algunas capacidades recientes pueden requerir Responses API.  
**Riesgo:** diferencias de soporte por modelo o región.

## Condición de revisión

Model selection is governed by ADR-011. Change API style only for a demonstrated limitation.
