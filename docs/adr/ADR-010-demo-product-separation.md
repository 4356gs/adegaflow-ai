# ADR-010: Separación entre demo y producto futuro

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

Los datos y acciones del hackathon son simulados, pero el código no debe quedar atado a un único guion.

## Decisión

Introducir `DEMO_MODE`, datos semilla externos, interfaces de repositorio y tools, y adapters explícitos para CRM/stock simulados. No hardcodear el resultado de UC-001. Las capacidades futuras se documentan, no se implementan.

## Alternativas consideradas

- **Hardcodear la demo:** rápido, pero inválido y frágil.
- **Construir infraestructura productiva completa:** excede plazo.
- **Ramas separadas demo/producto:** genera divergencia prematura.

## Consecuencias

**Positivas:** demo reproducible y ruta de evolución.  
**Negativas:** pequeña capa adicional de configuración.  
**Riesgo:** abstracciones especulativas; solo se crean interfaces utilizadas.

## Condición de revisión

Revisar al incorporar el primer cliente o integración real.
