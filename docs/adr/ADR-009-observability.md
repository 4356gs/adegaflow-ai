# ADR-009: Observabilidad ligera

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

La demo necesita trazabilidad funcional y diagnóstico, pero no una plataforma completa de observabilidad.

## Decisión

Usar logs JSON en stdout, `correlation_id`, tablas `agent_runs` y `tool_executions`, duración por paso y errores tipados. No desplegar OpenTelemetry, Prometheus o Grafana.

## Alternativas consideradas

- **Solo logs de texto:** insuficientes para UI y análisis.
- **Stack completo de observabilidad:** potente, pero desproporcionado.
- **Servicios SaaS:** añaden dependencia y configuración.

## Consecuencias

**Positivas:** visible en la demo, fácil de depurar, poco coste.  
**Negativas:** sin dashboards operativos avanzados.  
**Riesgo:** crecimiento de payloads; se registran resúmenes.

## Condición de revisión

Añadir OpenTelemetry cuando existan múltiples servicios o requisitos de operación.
