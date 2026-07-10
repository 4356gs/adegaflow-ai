# ADR-011: Baseline de modelo Qwen para el Sprint 2

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI
- **Modifica:** ADR-004

## Contexto

La documentación oficial actual recomienda `qwen3.7-plus` como modelo equilibrado para nuevas aplicaciones y confirma que soporta function calling y structured output. El baseline anterior utilizaba `qwen3.6-plus`.

El proyecto necesita:

- function calling;
- salida JSON;
- buen rendimiento multilingüe;
- latencia razonable;
- un fallback económico;
- una integración estable antes de la fecha límite.

La guía general recomienda Responses API para integraciones nuevas. Sin embargo, Chat Completions ofrece en un único endpoint el function calling y el JSON Object mode que requiere el MVP. Cambiar simultáneamente de modelo y estilo de API antes del spike aumentaría variables de riesgo.

## Decisión

1. Utilizar `qwen3.7-plus` como modelo principal del Sprint 2.
2. Utilizar `qwen3.6-flash` como fallback económico y para reparaciones simples.
3. Mantener OpenAI-compatible Chat Completions durante el MVP.
4. Ejecutar el spike con thinking desactivado.
5. Configurar modelo, endpoint y parámetros mediante variables de entorno.
6. No utilizar alias versionado por fecha hasta confirmar disponibilidad en la cuenta del hackathon.
7. Comparar Responses API solo como experimento no bloqueante si el camino principal ya funciona.

## Alternativas consideradas

### Mantener `qwen3.6-plus`

Sigue siendo compatible, pero ya no es la recomendación principal para nuevas aplicaciones.

### Utilizar `qwen3.7-max`

Mayor capacidad, pero coste y latencia potencialmente superiores para un flujo que no requiere el nivel más alto.

### Utilizar Responses API como baseline

Es la recomendación general para integraciones nuevas y ofrece herramientas adicionales. Se descarta temporalmente porque:

- el MVP no necesita built-in tools;
- el flujo requiere tools propias;
- JSON mode y Chat Completions tienen ejemplos directos;
- mantener un único estilo reduce incertidumbre.

## Consecuencias

### Positivas

- modelo actual recomendado;
- soporte de function calling;
- soporte de JSON Object mode;
- mejor baseline de calidad;
- fallback rápido y económico;
- mínima modificación de la arquitectura.

### Negativas

- no se adopta la API más nueva como camino principal;
- se mantiene manualmente el historial de mensajes durante tool calling;
- JSON Object mode garantiza JSON válido, pero no conformidad con el esquema.

### Riesgos

- diferencias de disponibilidad por cuenta o región;
- cambios de alias del modelo;
- latencia superior a la aceptable.

## Mitigación

- prueba en vivo durante el primer bloque del Sprint 2;
- validación Pydantic;
- timeout;
- reintentos controlados;
- fallback;
- variables configurables.

## Condición de revisión

Revisar únicamente si:

- `qwen3.7-plus` no está disponible;
- function calling falla de forma reproducible;
- la latencia bloquea la demo;
- Responses API reduce de forma probada complejidad o errores.
