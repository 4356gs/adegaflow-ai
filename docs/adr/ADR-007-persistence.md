# ADR-007: Persistencia SQLite para el MVP

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

La demo usa una organización, pocos usuarios, una instancia y un volumen de datos reducido.

## Decisión

Usar SQLite en volumen persistente, SQLAlchemy 2.0, Alembic y un solo worker. Mantener repositorios que permitan migrar a PostgreSQL.

## Alternativas consideradas

- **PostgreSQL gestionado:** más sólido, pero añade servicio, credenciales y coste operativo.
- **Archivos JSON:** simples, pero pobres para relaciones, transacciones y trazabilidad.
- **Base en memoria:** no demuestra persistencia.

## Consecuencias

**Positivas:** cero servicio adicional, backup fácil, suficiente para la demo.  
**Negativas:** concurrencia y escalabilidad limitadas.  
**Riesgo:** bloqueo con múltiples workers; se fija uno.

## Condición de revisión

Migrar a PostgreSQL antes de multitenencia, concurrencia real o producción.
