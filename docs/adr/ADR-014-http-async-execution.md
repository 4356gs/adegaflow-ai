# ADR-014: API HTTP y ejecución asíncrona local recuperable

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-18
- **Decisores:** Equipo técnico AdegaFlow AI
- **Relacionados:** ADR-003, ADR-007, ADR-008, ADR-009, ADR-010, ADR-013

## Contexto

El Sprint 2 Bloque 7 cerró el flujo funcional del backend. Un run nuevo puede
analizar una consulta, recuperar memoria, consultar catálogo y stock, validar
una recomendación, calcular una cotización, generar dos artefactos y persistir
acciones internas. El camino feliz termina en `needs_review` porque la propuesta
y el correo todavía requieren intervención humana.

El Sprint 2 Bloque 8 debe hacer UC-001 invocable por HTTP sin mantener abierta
una petición durante las llamadas a Qwen. También debe permitir polling,
reintentos controlados y una lectura estable para la futura aplicación web.

El MVP utiliza SQLite y se desplegará con un solo proceso API. Introducir Redis,
Celery, RabbitMQ o un servicio gestionado de colas aumentaría despliegue,
operación y superficie de fallo antes de validar el producto.

## Decisión

### 1. Límite HTTP

Los recursos de producto se publican exclusivamente bajo `/api/v1`. `/health`
permanece sin versión para comprobaciones de proceso y contenedor.

El router sin versión no incluirá endpoints de producto. Esto evita que cada
ruta quede publicada accidentalmente dos veces.

### 2. Contrato mínimo

El bloque expone:

- creación, listado y consulta de inquiries;
- creación asíncrona de agent runs;
- listado resumido de runs para la futura bandeja;
- polling del estado y paso actual;
- eventos ordenados con cursor por secuencia;
- resultado comercial expandido y tipado;
- reintento explícito de fallos recuperables;
- oportunidad y memoria mediante lecturas tipadas;
- envelope uniforme de errores.

La aprobación o edición de artefactos no forma parte del Bloque 8.

### 3. Dispatcher local

Se implementará un dispatcher in-process con:

- una cola `asyncio.Queue` acotada;
- un único consumidor iniciado y detenido mediante el lifespan de FastAPI;
- una interfaz inyectable para sustituirlo en pruebas;
- una sesión SQLAlchemy independiente por ejecución;
- procesamiento secuencial para limitar contención de escritura en SQLite;
- persistencia del run como `queued` antes de encolarlo;
- respuesta HTTP `202 Accepted` después de confirmar la transacción.

El consumidor puede delegar el orquestador síncrono a un thread mediante
`asyncio.to_thread`. El event loop no ejecuta llamadas bloqueantes de Qwen ni
operaciones prolongadas de SQLAlchemy.

### 4. Durabilidad declarada

La cola local no es durable. No se intentará presentarla como tal.

Al iniciar el proceso, los runs que quedaron `queued` o `running` se consideran
interrumpidos por el proceso anterior. Se cierran como:

```text
status = failed
current_step = failed
error_code = RUN_INTERRUPTED
```

La recuperación registra `run_interrupted` y permite un retry explícito. No se
reanuda automáticamente una llamada a Qwen ni se repite una escritura interna a
ciegas.

Esta política requiere ejecutar un único worker Uvicorn. Múltiples procesos,
alta disponibilidad y recuperación automática requieren una cola durable y
quedan fuera del MVP.

### 5. Idempotencia de comandos HTTP

`POST /inquiries`, `POST /inquiries/{id}/agent-runs` y
`POST /agent-runs/{id}/retry` requieren `Idempotency-Key`.

La migración del bloque añade:

- `inquiries.submission_key`, nullable y único para compatibilidad histórica;
- `agent_runs.request_key`, nullable y único;
- `agent_runs.retry_of_run_id`, FK nullable a `agent_runs`.

Reglas:

- clave nueva: crear y devolver el recurso;
- misma clave y mismo comando: devolver el recurso existente;
- misma clave aplicada a otro comando lógico: `IDEMPOTENCY_CONFLICT`;
- la clave se valida antes de encolar;
- repetir el HTTP POST nunca encola dos veces el mismo run.

No se reutiliza `internal_action_receipts`: esos receipts protegen las acciones
de negocio dentro de un run, mientras las claves HTTP protegen comandos y
recursos públicos.

### 6. Semántica de retry

Un retry nunca reinicia ni sobrescribe el run original. Crea un nuevo
`agent_run` con:

- la misma inquiry;
- nuevo ID y correlation ID;
- nuevo `request_key`;
- `retry_of_run_id` apuntando al intento anterior;
- estado inicial `queued`;
- prompts y modelo efectivos vigentes al crear el nuevo intento.

Solo se permite sobre un run terminal con código expresamente recuperable. La
allowlist inicial incluye:

- `MODEL_TIMEOUT`;
- `MODEL_RATE_LIMIT`;
- `QWEN_TIMEOUT`;
- `QWEN_RATE_LIMITED`;
- `QWEN_CONNECTION_FAILED`;
- `PERSISTENCE_ERROR`;
- `RUN_INTERRUPTED`;
- errores equivalentes del adaptador clasificados como transitorios.

No se permite retry cuando:

- el run continúa `queued` o `running`;
- terminó correctamente y espera revisión humana;
- agotó límites agentic;
- la entrada es inválida;
- requiere corrección del usuario;
- existe un conflicto no recuperable.

La respuesta pública calcula `retryable` desde una política cerrada; no confía
en un booleano enviado por el cliente.

### 7. Resultado público

El endpoint de resultado ensambla un read model desde las tablas autoritativas.
Puede incluir:

- análisis y campos faltantes;
- recomendación validada;
- quote e items;
- propuesta y email draft;
- oportunidad y seguimiento;
- referencias resumidas de memoria;
- warnings y acciones ejecutadas.

No devuelve cadena de pensamiento, respuestas crudas de Qwen, API keys,
direcciones de muestras, identificadores fiscales ni payloads técnicos internos.

### 8. Polling y paginación

El polling usa `GET`, no WebSocket ni SSE.

- el estado del run es una lectura completa e idempotente;
- eventos aceptan `after_sequence` y `limit`;
- listados usan límites acotados y orden estable;
- no se realiza long polling;
- el cliente decide su intervalo y deja de consultar en estado terminal.

### 9. Errores HTTP

Todos los errores públicos utilizan:

```json
{
  "error": {
    "code": "RUN_NOT_RETRYABLE",
    "message": "The agent run cannot be retried.",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

Mapeo mínimo:

| Condición | HTTP |
|---|---:|
| entrada o header inválido | 422 |
| recurso inexistente | 404 |
| clave idempotente incompatible | 409 |
| estado no permite la operación | 409 |
| cola local no acepta trabajo | 503 |
| error interno no clasificado | 500 |

Los mensajes son seguros y no exponen stack traces.

## Alternativas consideradas

### Ejecutar el orquestador dentro de la petición

Descartada porque la latencia de Qwen puede superar timeouts de proxy y ofrece
una experiencia HTTP frágil.

### `FastAPI.BackgroundTasks` sin dispatcher

Descartada como mecanismo principal porque no controla concurrencia, no ofrece
una cola observable y facilita múltiples escritores simultáneos sobre SQLite.

### Reanudar automáticamente runs interrumpidos

Descartada porque el proceso no puede demostrar si una llamada externa terminó.
El retry explícito conserva mejor auditoría y control.

### Mutar el mismo run durante retry

Descartada porque sobrescribe el intento anterior, mezcla eventos y dificulta
reconstruir fallos.

### Redis y Celery

Descartados para el MVP. Son adecuados cuando se requieran múltiples workers,
durabilidad, scheduling, backpressure distribuido o alta disponibilidad.

### WebSockets o Server-Sent Events

Descartados porque polling sobre estado persistido cubre la demo con menos
infraestructura y menos contratos.

## Consecuencias

### Positivas

- UC-001 queda invocable sin bloquear la petición;
- contrato estable para Sprint 3;
- SQLite recibe un solo flujo de escritura prolongado cada vez;
- reintentos auditables sin sobrescribir runs;
- recuperación segura y explícita tras reinicios;
- no se introduce infraestructura operativa adicional.

### Negativas

- la cola se pierde al reiniciar;
- el throughput queda limitado a una ejecución simultánea;
- un despliegue con varios workers es incompatible;
- el retry vuelve a ejecutar el flujo completo para la misma inquiry;
- se añaden campos persistentes para idempotencia y relación entre intentos.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| run perdido en reinicio | marcar `RUN_INTERRUPTED` y permitir retry |
| doble submit HTTP | `Idempotency-Key` persistida antes de encolar |
| contención SQLite | consumidor único y sesiones cortas |
| retry de un éxito | allowlist cerrada y estado terminal validado |
| endpoints duplicados sin versión | separar `/health` del router `/api/v1` |
| exposición de datos | read models explícitos y envelope seguro |
| cola saturada | capacidad acotada y respuesta `503` |

## Condición de revisión

Revisar esta decisión si se incorpora:

- más de un proceso o instancia API;
- PostgreSQL con concurrencia real;
- ejecución durable tras reinicios;
- prioridad o scheduling de jobs;
- cancelación;
- SLA operativo;
- integración externa con correo, CRM o calendario;
- autenticación multiusuario.
