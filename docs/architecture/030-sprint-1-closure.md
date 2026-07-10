# Cierre del Sprint 1

## Estado

**Sprint 1 completado.**

No se ha escrito código de producto.

## Decisiones tomadas

1. Arquitectura de monolito modular en monorepo.
2. Dos contenedores: Next.js y FastAPI.
3. FastAPI concentra orquestador, tools, dominio y persistencia.
4. SQLite con SQLAlchemy y Alembic para el MVP.
5. Qwen Cloud mediante API compatible con OpenAI.
6. Modelo principal configurable; baseline `qwen3.7-plus`.
7. Orquestador acotado por estados, máximo de rondas y tools.
8. Tools de lectura invocables por el modelo; escrituras internas controladas por el orquestador.
9. Sin LangChain, Qwen-Agent, MCP o vector DB en el camino crítico.
10. Memoria explícita por hechos, sin embeddings.
11. Procesamiento en segundo plano in-process con polling.
12. Trazabilidad en base de datos y logs JSON.
13. Despliegue en Alibaba Cloud ECS mediante Docker Compose.
14. Next.js será el único puerto público y actuará como proxy.
15. Track oficial: Autopilot Agent.
16. Revisión humana antes de cualquier comunicación externa.
17. Fecha interna de envío: 19 de julio de 2026.

## Decisiones condicionadas al spike

- confirmar disponibilidad y comportamiento de `qwen3.7-plus`;
- confirmar salida JSON y function calling en la cuenta internacional;
- comparar latencia con `qwen3.6-flash`;
- decidir si una sola llamada de recomendación basta o se requieren dos fases;
- ajustar máximo de rondas según pruebas.

Estas decisiones no reabren la arquitectura general.

## Riesgos residuales

- tiempo limitado;
- alta dependencia de Qwen Cloud y conectividad;
- procesador in-process no durable;
- SQLite con un solo worker;
- falta de validación sectorial real;
- despliegue ECS pendiente;
- posible latencia de múltiples rondas.

## Criterio de entrada al Sprint 2

El Sprint 2 comienza con un único objetivo:

> implementar y validar el núcleo funcional de UC-001 desde la consulta hasta una respuesta estructurada con tools reales.

Orden obligatorio:

1. spike Qwen;
2. contratos y esquemas;
3. datos semilla;
4. tools;
5. orquestador;
6. persistencia;
7. pruebas;
8. interfaz posteriormente.

## Primer documento operativo del Sprint 2

`docs/implementation/050-sprint-2-plan.md`

Debe convertir el backlog arquitectónico en tareas ejecutables, con orden de commits, pruebas y criterios de aceptación.
