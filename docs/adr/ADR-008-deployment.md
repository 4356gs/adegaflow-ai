# ADR-008: Despliegue en Alibaba Cloud ECS

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

El hackathon exige prueba de backend ejecutándose en Alibaba Cloud.

## Decisión

Usar una instancia ECS Linux con Docker Compose. Exponer Next.js en el puerto 3000; FastAPI y SQLite permanecen en red/volumen internos. Despliegue manual documentado por SSH.

## Alternativas consideradas

- **Function Compute:** menos servidor, más adaptación.
- **ACK/Kubernetes:** sobreingeniería.
- **Vercel:** útil para web, pero no prueba por sí solo backend en Alibaba Cloud.
- **Local:** no cumple.

## Consecuencias

**Positivas:** evidencia clara, control total, coherencia con Docker.  
**Negativas:** mantenimiento manual y una sola instancia.  
**Riesgo:** configuración de red/credenciales; se despliega antes del cierre funcional.

## Condición de revisión

Revisar a servicios gestionados después del hackathon.
