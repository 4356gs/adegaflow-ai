# ADR-006: Memoria comercial

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

El producto debe recordar preferencias del comprador entre sesiones, pero el volumen de datos es pequeño y estructurado.

## Decisión

Persistir memorias como hechos explícitos categorizados por comprador, con confianza, fuente e invalidación. Recuperar por `customer_id` y categoría. No usar embeddings ni vector DB.

## Alternativas consideradas

- **Guardar solo resumen JSON en customer:** simple, pero poco auditable.
- **Vector DB/RAG:** más flexible, pero excesivo y difícil de validar.
- **Historial completo en prompt:** consume contexto y mezcla información irrelevante.

## Consecuencias

**Positivas:** trazabilidad, bajo coste, corrección sencilla.  
**Negativas:** menor recuperación semántica.  
**Riesgo:** memorias duplicadas; se mitigará con normalización y deduplicación.

## Condición de revisión

Revisar embeddings cuando existan documentos o miles de interacciones por cliente.
