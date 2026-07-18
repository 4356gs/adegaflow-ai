# Sprint 2 Bloque 8 — API y ejecución asíncrona

- **Estado:** Ready for implementation
- **Sprint:** 2 — Núcleo funcional
- **Bloque:** 8
- **Baseline:** `644d12f`
- **Rama documental:** `docs/sprint2-block8-plan`
- **Rama de implementación prevista:** `feat/sprint2-async-run-api`
- **Fecha:** 2026-07-18
- **ADR vinculante:** ADR-014
- **Backlog:** AF-013, AF-033, AF-034, AF-035

## Objetivo

Exponer UC-001 mediante una API REST tipada que acepte una consulta, cree un
agent run persistente, lo procese fuera de la petición HTTP y permita consultar
estado, eventos, resultado y reintentos seguros.

El bloque convierte el núcleo funcional ya probado en una capacidad invocable.
No añade nuevas decisiones comerciales ni modifica el resultado del agente.

## Alcance incluido

- ADR-014 aceptado;
- migración reversible para claves de submission, claves de run y relación de
  retry;
- schemas Pydantic estrictos de request y response;
- envelope uniforme de errores;
- dependencias FastAPI para sesiones y servicios;
- endpoints versionados para inquiries y agent runs;
- listado resumido para la futura bandeja;
- polling de estado y eventos;
- read model expandido del resultado;
- lecturas de oportunidad y memoria activa;
- dispatcher local con consumidor único;
- recuperación de runs interrumpidos al iniciar;
- retry explícito mediante un run nuevo;
- idempotencia persistente de comandos POST;
- logs y eventos seguros del ciclo HTTP/dispatcher;
- tests de contratos, integración, dispatcher, recuperación y migración;
- documentación y evidencia de cierre.

## Fuera de alcance

- frontend Next.js;
- autenticación, autorización o multitenencia;
- aprobación, rechazo o edición de artefactos;
- envío real de correo;
- CRM o calendario externos;
- reserva o modificación de stock;
- PDF o HTML final;
- WebSockets, SSE o long polling;
- cancelación o prioridad de runs;
- reanudación desde un paso intermedio;
- retry automático del flujo completo;
- Redis, Celery, RabbitMQ o cola durable;
- múltiples workers o instancias API;
- PostgreSQL;
- rate limiting público;
- CORS para un frontend externo;
- endpoints de demo reset;
- pruebas end-to-end finales, despliegue y evidencia del hackathon;
- implementación del Bloque 9 o Sprint 3.

## Precondiciones

- `main` limpio en `644d12f` o su merge posterior equivalente;
- Alembic head `0004_internal_actions`;
- Bloques 0-7 implementados;
- ADR-013 y `063-internal-actions.md` vigentes;
- `make check-api` en verde;
- un solo worker durante ejecución local y de demo.

## Decisiones de diseño

### 1. Separación de routers

La aplicación publicará:

```text
/health
/api/v1/inquiries
/api/v1/agent-runs
/api/v1/opportunities
/api/v1/customers
```

`main.py` incluirá el router de producto una sola vez con prefijo `/api/v1` y
el router de health por separado. No se publicarán alias sin versión para rutas
de producto.

### 2. Envelope de errores

Contrato:

```json
{
  "error": {
    "code": "INQUIRY_NOT_FOUND",
    "message": "Inquiry was not found.",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

Reglas:

- `code` pertenece a una taxonomía pública cerrada;
- `message` es seguro y estable para humanos;
- `details` contiene únicamente campos accionables y no sensibles;
- `correlation_id` se acepta o genera por request;
- ninguna respuesta contiene stack trace o excepción interna.

### 3. Crear inquiry

`POST /api/v1/inquiries`

Header obligatorio:

```text
Idempotency-Key: 1-160 caracteres seguros
```

Request:

```json
{
  "source": "manual",
  "raw_message": "We are looking for 600 bottles for Germany.",
  "customer_id": null
}
```

Validación:

- source permitido: `manual` o `demo`;
- mensaje después de trim: 1-10 000 caracteres;
- customer UUID existente cuando se envía;
- no aceptar `email_simulated` desde este endpoint;
- no aceptar extracted data, status, timestamps ni IDs creados por el cliente.

Respuesta nueva: `201 Created`. Una repetición equivalente devuelve `200 OK`
con el mismo recurso y no repite efectos. Ambas respuestas deben aparecer en
OpenAPI y tener pruebas de contrato.

### 4. Listar y consultar inquiries

`GET /api/v1/inquiries`

Parámetros:

- `status` opcional;
- `limit`, default 20, máximo 100;
- `offset`, default 0, máximo documentado;
- orden estable `received_at DESC, id DESC`.

`GET /api/v1/inquiries/{inquiry_id}` devuelve:

- mensaje fuente;
- source y status;
- idioma detectado;
- extracción validada;
- campos faltantes;
- customer ID;
- received_at;
- IDs resumidos de runs en orden descendente.

### 5. Crear agent run

`POST /api/v1/inquiries/{inquiry_id}/agent-runs`

Requiere `Idempotency-Key`. No acepta modelo, prompt, estado ni correlation ID
desde el body. Esos valores se derivan de configuración y registros vigentes.

Transacción:

1. validar inquiry y clave;
2. crear run `queued` y evento `run_created`;
3. persistir `request_key`;
4. commit;
5. encolar el ID;
6. responder `202 Accepted`.

Respuesta:

```json
{
  "agent_run_id": "uuid",
  "inquiry_id": "uuid",
  "status": "queued",
  "current_step": "queued",
  "correlation_id": "uuid",
  "retry_of_run_id": null,
  "poll_url": "/api/v1/agent-runs/uuid"
}
```

Si el commit se confirma pero el dispatcher rechaza el trabajo, el run se
cierra con `DISPATCH_FAILED` y la API responde `503` con la referencia segura.

### 6. Dispatcher

Contrato interno:

```text
RunDispatcher.enqueue(run_id) -> None
RunDispatcher.start() -> None
RunDispatcher.stop() -> None
```

Implementación MVP:

- `asyncio.Queue` con capacidad configurada y acotada;
- un solo consumer;
- `asyncio.to_thread` para ejecutar el orquestador síncrono;
- una nueva `SessionLocal` por run;
- commit/rollback regidos por los servicios existentes;
- excepciones convertidas a estado seguro cuando la base está disponible;
- cierre del consumer desde lifespan;
- dispatcher fake o inline en tests.

Configuración:

```text
ASYNC_RUN_QUEUE_CAPACITY=10
```

El valor es un entero positivo con máximo 100. El número de consumidores queda
fijo en uno y no se convierte en una opción de entorno durante el MVP.

No se comparte la sesión HTTP con el trabajo de background.

### 7. Recuperación al iniciar

Antes de aceptar trabajo nuevo:

1. buscar runs con `status in (queued, running)`;
2. marcarlos `failed/failed`;
3. asignar `RUN_INTERRUPTED` y mensaje seguro;
4. cerrar tools que hayan quedado `started` como `failed` cuando proceda;
5. registrar `run_interrupted`;
6. commit;
7. iniciar el consumer.

No se recuperan runs históricos de antes del Bloque 8 y ya terminales.

### 8. Polling de estado

`GET /api/v1/agent-runs/{agent_run_id}` devuelve:

- IDs de run, inquiry, retry parent y correlation;
- status y current step;
- started/completed timestamps;
- modelo y versiones de prompt;
- error público seguro;
- `retryable` calculado;
- resumen de referencias disponibles;
- `last_event_sequence`;
- URLs relativas a events y result.

No devuelve todos los eventos ni el resultado comercial completo.

### 9. Listado de runs

`GET /api/v1/agent-runs`

Filtros:

- `status` opcional;
- `inquiry_id` opcional;
- `limit` y `offset` acotados;
- orden estable por creación descendente.

Cada elemento contiene solo lo necesario para una bandeja: IDs, estado, paso,
empresa cuando exista, mercado, received/started/completed times, error code y
retryable.

### 10. Eventos

`GET /api/v1/agent-runs/{agent_run_id}/events`

Parámetros:

- `after_sequence`, default 0;
- `limit`, default 100, máximo 200.

Respuesta:

```json
{
  "agent_run_id": "uuid",
  "events": [
    {
      "sequence": 1,
      "event_type": "run_created",
      "step": "queued",
      "payload": {},
      "created_at": "2026-07-18T18:00:00Z"
    }
  ],
  "last_sequence": 1,
  "terminal": false
}
```

Los payloads ya persistidos se filtran mediante un schema público; no se
devuelve arbitrariamente todo JSON interno.

### 11. Resultado expandido

`GET /api/v1/agent-runs/{agent_run_id}/result`

Disponibilidad:

- `409 RUN_NOT_TERMINAL` mientras el run está `queued` o `running`;
- `200` para resultados terminales, incluidos parciales;
- `404` solo cuando el run no existe.

Secciones opcionales:

```text
inquiry
analysis
recommendation
quote
artifacts
customer
opportunity
followup
memory_summary
warnings
```

Quote, artifacts y acciones se recuperan de sus tablas. `result_payload` aporta
referencias y resultados parciales, pero no sustituye consultas autoritativas.

### 12. Retry

`POST /api/v1/agent-runs/{agent_run_id}/retry`

Requiere `Idempotency-Key` y body vacío.

Algoritmo:

1. recuperar run original;
2. exigir estado terminal;
3. calcular retryable mediante allowlist;
4. rechazar espera de revisión humana o error no recuperable;
5. crear un run nuevo para la misma inquiry;
6. asignar `retry_of_run_id`;
7. persistir `request_key` y `run_created`;
8. commit y enqueue;
9. responder `202` con el nuevo run.

No se copian `result_payload`, eventos, tools, quote, artefactos o receipts al
nuevo run.

### 13. Lecturas comerciales

`GET /api/v1/opportunities/{opportunity_id}` devuelve el registro CRM simulado,
customer, inquiry, quote, artefactos y follow-up mediante schemas públicos.

`GET /api/v1/customers/{customer_id}/memory` devuelve solo memorias activas,
ordenadas y paginadas. No permite crear, editar o invalidar memoria.

### 14. Idempotencia

Claves:

- 1-160 caracteres;
- trim obligatorio;
- conjunto seguro ASCII documentado;
- no se registran completas en logs;
- pueden incluirse truncadas o resumidas mediante hash en eventos.

Conflictos:

| Situación | Resultado |
|---|---|
| misma key y mismo inquiry submit | devolver inquiry existente |
| misma key para otro contenido | 409 `IDEMPOTENCY_CONFLICT` |
| misma key y mismo run command | devolver run existente sin enqueue |
| misma key para otra inquiry | 409 `IDEMPOTENCY_CONFLICT` |
| misma retry key y mismo parent | devolver retry existente |
| misma retry key con otro parent | 409 `IDEMPOTENCY_CONFLICT` |

### 15. Taxonomía pública adicional

- `IDEMPOTENCY_KEY_REQUIRED`;
- `IDEMPOTENCY_CONFLICT`;
- `INQUIRY_NOT_FOUND`;
- `CUSTOMER_NOT_FOUND`;
- `AGENT_RUN_NOT_FOUND`;
- `OPPORTUNITY_NOT_FOUND`;
- `RUN_NOT_TERMINAL`;
- `RUN_NOT_RETRYABLE`;
- `RUN_ALREADY_ACTIVE`;
- `DISPATCH_QUEUE_FULL`;
- `DISPATCH_FAILED`;
- `RUN_INTERRUPTED`;
- `INVALID_INPUT`;
- `INTERNAL_ERROR`.

Los códigos internos de Qwen y orquestación se conservan en persistencia y se
mapean sin perder la causa segura.

## Migración `0005_http_async_runs`

Añade:

### `inquiries`

- `submission_key VARCHAR(160) NULL`;
- índice único cuando no es null.

### `agent_runs`

- `request_key VARCHAR(160) NULL`;
- `retry_of_run_id VARCHAR(36) NULL`;
- FK self-reference con `ON DELETE SET NULL`;
- índice único para request key;
- índice para retry parent.

La migración debe conservar seeds y runs históricos con valores null. El
downgrade elimina primero índices y FK antes de las columnas mediante batch
operations compatibles con SQLite.

## Manejo de errores

| Condición | Resultado |
|---|---|
| inquiry inexistente | 404, no crear run |
| customer hint inexistente | 404, no crear inquiry |
| mensaje fuera de límites | 422 |
| falta Idempotency-Key | 422 |
| key con otro contenido | 409 |
| queue full | cerrar run con error seguro, 503 |
| run no terminal al pedir resultado | 409 |
| retry de run activo | 409 |
| retry de human review | 409 |
| restart con run activo | `RUN_INTERRUPTED`, retryable |
| excepción del worker | run failed cuando se puede persistir |
| fallo que impide persistir estado | log crítico; no afirmar éxito |

## Tests requeridos

### Migración

- upgrade desde `0004`;
- columnas, FK e índices;
- claves únicas no nulas;
- múltiples filas históricas con null;
- retry parent válido;
- downgrade reversible;
- SQLite foreign keys activas.

### Schemas y errores

- límites de mensaje, key, paginación y UUID;
- enums cerrados;
- campos extra rechazados;
- timestamps UTC;
- error envelope para validación y excepciones;
- ausencia de stack trace y secretos.

### Inquiries

- crear manual y demo;
- customer existente opcional;
- rechazar customer inexistente;
- list/filter/order/pagination;
- get completo;
- idempotencia equivalente;
- conflicto de contenido.

### Agent runs

- POST confirma `queued` antes de enqueue;
- devuelve `202`;
- misma key no duplica ni reencola;
- get de cada estado;
- listado filtrado y ordenado;
- polling durante transición;
- Qwen no configurado produce error seguro.

### Dispatcher

- lifecycle start/stop;
- un solo consumidor;
- sesiones independientes;
- FIFO observable;
- queue full;
- excepción controlada;
- no bloquear event loop;
- cierre limpio;
- no ejecutar dos veces el mismo run.

### Recovery y retry

- queued interrumpido pasa a failed;
- running interrumpido pasa a failed;
- tool started se cierra de forma coherente;
- `run_interrupted` en orden;
- código recuperable crea nuevo run;
- human review no permite retry;
- código no recuperable rechaza;
- retry parent persistido;
- retry idempotente;
- original inmutable.

### Events y result

- cursor `after_sequence` sin huecos ni duplicados;
- límite máximo;
- eventos públicos sin PII innecesaria;
- resultado no terminal devuelve 409;
- camino feliz contiene quote, artifacts y acciones;
- resultado parcial conserva secciones disponibles;
- tablas autoritativas prevalecen sobre referencias;
- oportunidad y memoria recuperables.

### Rutas

- endpoints de producto solo bajo `/api/v1`;
- `/health` sigue disponible;
- no existe `/inquiries` sin versión;
- OpenAPI contiene responses y schemas esperados.

## Criterios de aceptación

1. Una inquiry válida puede crearse por HTTP.
2. Repetir el submit equivalente no duplica la inquiry.
3. Iniciar un run responde `202` después de persistir `queued`.
4. El trabajo continúa fuera de la petición HTTP.
5. El cliente puede observar estado, paso y eventos mediante polling.
6. El run feliz termina `needs_review` con resultado expandido.
7. Quote, propuesta, correo, oportunidad, seguimiento y memoria son legibles.
8. Un restart convierte trabajo interrumpido en fallo seguro y retryable.
9. Un retry recuperable crea un run nuevo y conserva el original.
10. Un run que espera revisión humana no puede reintentarse.
11. Repetir una key de run o retry no duplica ni reencola.
12. Los errores usan un envelope uniforme con correlation ID.
13. Ningún endpoint expone secretos, chain of thought o respuestas crudas.
14. Las rutas de producto solo existen bajo `/api/v1`.
15. La migración es reversible.
16. Ruff, mypy strict y pytest pasan.

## Definition of Done

- ADR-014 aceptado;
- documentación arquitectónica alineada;
- migración `0005_http_async_runs` reversible;
- schemas HTTP estrictos;
- dependencias y errores uniformes;
- endpoints de inquiries y runs;
- listados acotados y ordenados;
- polling de estado y eventos;
- resultado expandido tipado;
- oportunidad y memoria legibles;
- dispatcher local con un consumidor;
- recuperación explícita de interrupciones;
- retry mediante run nuevo;
- idempotencia HTTP persistente;
- cobertura de contratos, integración, dispatcher y migración;
- OpenAPI verificado;
- README, changelog y verification actualizados al cierre;
- `make check-api` en verde;
- un solo worker documentado;
- capacidad de cola documentada y validada;
- sin frontend, aprobación, integraciones externas o cola durable.

## Orden de implementación

1. migración y persistencia de claves/retry parent;
2. schemas HTTP y error envelope;
3. repositorios de inquiry, listados y read models;
4. dependencias FastAPI y separación de routers;
5. endpoints de inquiry;
6. dispatcher y lifecycle;
7. endpoints de creación, listado y polling de runs;
8. recovery y retry policy;
9. events, result, opportunity y memory reads;
10. tests de migración y unidad;
11. tests de integración HTTP y dispatcher;
12. OpenAPI y documentación de cierre.

No se comenzará el Bloque 9 ni Sprint 3 hasta cerrar implementación, calidad,
PR y documentación del Bloque 8.
