# ADR-001: Arquitectura general

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

El MVP debe completar un flujo agentic real en diez días, desplegarse en Alibaba Cloud y seguir siendo comprensible para jueces y futuros colaboradores.

## Decisión

Adoptar un monolito modular en monorepo con dos procesos desplegables: Next.js para la web y FastAPI para la API. El backend contiene módulos internos separados para dominio, orquestación, tools, IA, repositorios y persistencia.

## Alternativas consideradas

- **Microservicios:** rechazados por operación y coordinación innecesarias.
- **Aplicación full-stack solo Next.js:** rechazada porque Python/FastAPI simplifica IA, validación y dominio.
- **Monolito de un solo proceso:** viable, pero reduce separación tecnológica y claridad.

## Consecuencias

**Positivas:** velocidad, pruebas sencillas, despliegue reproducible, límites claros.  
**Negativas:** no escala componentes de forma independiente.  
**Riesgo aceptado:** un fallo del backend afecta todo el flujo.

## Condición de revisión

Revisar cuando exista más de un equipo, carga sostenida o necesidad de escalar módulos por separado.
