# Plan de implementación del Sprint 2

## Principio

Construir verticalmente. Cada bloque debe dejar una capacidad ejecutable y probada.

## Secuencia

### Bloque 0 — Bootstrap

- crear estructura del repositorio;
- inicializar FastAPI;
- configuración tipada;
- logging;
- health endpoint;
- pytest, Ruff y mypy;
- Dockerfile API;
- `.env.example`.

**Salida:** API arranca y pasa calidad básica.

### Bloque 1 — Spike Qwen

- ejecutar S-01 a S-07;
- documentar resultados;
- confirmar ADR-011;
- implementar `QwenClient` mínimo.

**Salida:** integración aprobada.

### Bloque 2 — Dominio y persistencia

- entidades SQLAlchemy;
- schemas Pydantic;
- migración inicial;
- repositorios;
- seed loader;
- transacciones.

**Salida:** catálogo, stock, compradores e inquiries persistentes.

### Bloque 3 — Tools de lectura

- `search_catalog`;
- `get_product_details`;
- `check_stock`;
- `retrieve_customer_history`.

**Salida:** contratos y tests unitarios.

### Bloque 4 — Análisis de consulta

- prompt `inquiry_analysis.v1`;
- JSON Object mode;
- validación;
- reparación controlada;
- persistencia de extracción.

**Salida:** consulta analizada de forma reproducible.

### Bloque 5 — Orquestación y recomendación

- estado del run;
- tool registry;
- ciclo acotado;
- selección;
- validación determinista;
- eventos;
- límites.

**Salida:** productos válidos y trazabilidad.

### Bloque 6 — Cotización y artefactos

- `calculate_quote`;
- `generate_proposal`;
- `draft_email`;
- reglas monetarias;
- estado `needs_review`.

**Salida:** propuesta y correo persistidos.

### Bloque 7 — Acciones internas

- `create_crm_opportunity`;
- `create_followup_task`;
- `save_customer_memory`;
- idempotency keys.

**Salida:** flujo completo persistente.

### Bloque 8 — API y ejecución asíncrona

- endpoints;
- background task;
- polling de estado;
- retry;
- manejo de errores.

**Salida:** UC-001 invocable por HTTP.

### Bloque 9 — Pruebas y documentación

- tests unitarios;
- integración con Qwen mock;
- test live opcional;
- end-to-end backend;
- README;
- comandos de demo.

**Salida:** Sprint 2 candidato a cierre.

## Orden de commits recomendado

1. `chore: bootstrap FastAPI service and quality tooling`
2. `test: add Qwen Cloud integration spike`
3. `feat: add domain models persistence and demo seeds`
4. `feat: implement catalog stock and customer tools`
5. `feat: add structured inquiry analysis`
6. `feat: implement bounded tool-calling orchestrator`
7. `feat: add quote proposal and email draft generation`
8. `feat: persist opportunity follow-up and memory`
9. `feat: expose agent run API and events`
10. `test: cover backend end-to-end workflow`
11. `docs: document Sprint 2 setup and evidence`

## Reglas de implementación

- ninguna función de dominio depende de FastAPI;
- ninguna tool conoce el SDK Qwen;
- aritmética monetaria fuera del modelo;
- no hardcodear respuesta del escenario principal;
- fallos de Qwen no corrompen transacciones;
- cada escritura posee idempotency key;
- tests live de Qwen se marcan y no se ejecutan por defecto;
- el código no persiste cadena de pensamiento.

## Estimación preliminar

| Bloque | Esfuerzo relativo |
|---|---:|
| Bootstrap | 1 |
| Spike | 2 |
| Datos y persistencia | 3 |
| Tools de lectura | 2 |
| Análisis | 2 |
| Orquestador | 5 |
| Cotización y artefactos | 3 |
| Acciones internas | 2 |
| API asíncrona | 3 |
| Pruebas y docs | 3 |

El orquestador es el punto de mayor riesgo. No debe ampliarse hasta completar el camino feliz.
