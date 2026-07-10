# Sprint 1 — Charter de arquitectura

## Identificación

- **Proyecto:** AdegaFlow AI
- **Sprint:** 1 — Arquitectura
- **Estado:** Completado
- **Fecha de cierre:** 2026-07-10
- **Objetivo único:** definir una solución técnica implementable, reproducible y alineada con el hackathon antes de escribir código de producto.

## Entradas

- Visión y alcance cerrados en el Sprint 0.
- Caso de uso principal UC-001.
- Restricción de uso central de Qwen Cloud.
- Requisito de despliegue del backend en Alibaba Cloud.
- Fecha límite oficial del hackathon: 2026-07-20 a las 14:00 PDT.

## Entregables

1. Arquitectura general.
2. Estructura del repositorio.
3. Modelo de datos.
4. Estrategia de orquestación del agente.
5. Contratos de herramientas.
6. Contratos de API.
7. Estrategia de prompts.
8. Estrategia de despliegue.
9. Observabilidad y manejo de errores.
10. Alineación con el hackathon.
11. ADR-001 a ADR-010.
12. Plan de entrega hasta la fecha límite.
13. Cierre del sprint.

## Criterios de aceptación

- La arquitectura soporta el flujo UC-001 de extremo a extremo.
- Qwen Cloud tiene una responsabilidad explícita y verificable.
- Los límites entre IA y lógica determinista están definidos.
- Las tools poseen contratos tipados.
- El flujo tiene límite de rondas y rutas de fallback.
- La persistencia es suficiente para memoria, CRM simulado y trazabilidad.
- El despliegue cumple el requisito de backend en Alibaba Cloud.
- La solución evita microservicios, vector DB, colas distribuidas y frameworks de agentes sin necesidad.
- Las decisiones relevantes están registradas mediante ADR.
- No se ha escrito código de producto.

## Definition of Done

- Todos los documentos están versionados en Markdown.
- Los ADR están aceptados para el MVP.
- El backlog de implementación puede derivarse sin inventar arquitectura.
- El repositorio objetivo está definido.
- Existen contratos de alto nivel para API, tools y datos.
- Los riesgos críticos tienen una mitigación arquitectónica.
- El Sprint 2 puede comenzar con un spike de Qwen Cloud y tool calling.

## Restricción de calendario

Quedan diez días naturales entre el cierre de este sprint y la fecha límite oficial. Por tanto:

- no se aceptarán cambios arquitectónicos amplios después del primer spike;
- el despliegue inicial se realizará antes de cerrar la interfaz;
- toda capacidad P1 queda subordinada al flujo P0;
- el 19 de julio se reserva como margen de corrección y envío.
