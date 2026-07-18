# Observabilidad y manejo de errores

## Objetivos

1. Entender qué ocurrió durante una ejecución.
2. Mostrar trazabilidad útil al usuario.
3. Diagnosticar fallos sin exponer secretos.
4. Medir latencia y estabilidad de la demo.
5. Reconstruir el orden funcional del run sin almacenar cadena de pensamiento.

## Capas de observabilidad

### Logs de aplicación

Formato JSON en stdout:

```json
{
  "timestamp": "2026-07-10T18:00:00Z",
  "level": "INFO",
  "service": "api",
  "correlation_id": "uuid",
  "agent_run_id": "uuid",
  "event": "tool_completed",
  "step": "checking_stock",
  "tool": "check_stock",
  "duration_ms": 14,
  "error_code": null
}
```

Campos comunes:

- timestamp;
- level;
- service o logger;
- correlation_id;
- agent_run_id;
- event;
- step;
- tool cuando aplique;
- duration_ms cuando aplique;
- error_code cuando aplique.

El mensaje comercial completo no se repite en logs.

### Trazabilidad funcional

Persistida en:

- `agent_runs`;
- `tool_executions`;
- `agent_run_events`.

Es la fuente para la futura interfaz y para inspección de pruebas.

#### `agent_runs`

Resume:

- estado global;
- paso actual;
- modelo efectivo;
- prompts;
- resultado;
- error seguro;
- timestamps;
- correlation ID.

#### `tool_executions`

Conserva:

- orden;
- nombre;
- entrada validada;
- salida resumida;
- estado;
- duración;
- error.

Cada intento cuenta, incluidos rechazos y reintentos.

#### `agent_run_events`

Conserva eventos de dominio y orquestación en orden estricto.

Eventos mínimos:

- run_created;
- step_changed;
- analysis_reused;
- analysis_completed;
- memory_retrieval_skipped;
- memory_retrieved;
- model_round_completed;
- tool_requested;
- tool_started;
- tool_succeeded;
- tool_failed;
- tool_rejected;
- recommendation_received;
- recommendation_rejected;
- recommendation_validated;
- run_completed;
- run_needs_review;
- run_failed.

El Bloque 7 añade:

- internal_actions_started;
- customer_resolution_started;
- customer_reused;
- customer_created;
- crm_opportunity_started;
- crm_opportunity_persisted;
- followup_task_started;
- followup_task_persisted;
- customer_memory_started;
- customer_memory_persisted;
- internal_action_reused;
- internal_action_rejected;
- internal_actions_rolled_back;
- internal_actions_completed.

El payload contiene resúmenes seguros, no respuestas completas del proveedor.

### Orden y correlación

- `correlation_id` correlaciona logs y persistencia.
- `agent_run_id` identifica una ejecución.
- `sequence` ordena tool executions por run.
- `sequence` ordena eventos por run.
- Las restricciones únicas evitan secuencias duplicadas.
- Una inquiry puede tener varios runs.

### Métricas mínimas derivadas

- duración total del run;
- duración por tool;
- número de llamadas a Qwen;
- número de tools;
- número de rechazos;
- reintentos;
- rondas consumidas;
- estado final;
- tokens si el proveedor los devuelve;
- causa de fallo;
- cantidad de productos recomendados;
- número de correcciones de recomendación.

No se desplegará Prometheus para el MVP.

## Tamaño y retención de payloads

Para evitar crecimiento innecesario:

- inputs de tools se almacenan ya validados;
- outputs se serializan mediante el envelope común;
- payloads grandes se resumen;
- no se conserva la respuesta completa del proveedor;
- no se duplica el mensaje comercial en cada evento;
- no se persiste cadena de pensamiento;
- result_payload conserva solo el resultado necesario para continuar el flujo.

## Taxonomía de errores

| Código | Tipo | Recuperable |
|---|---|---:|
| `INVALID_INPUT` | Entrada de usuario | No, requiere corrección |
| `INQUIRY_NOT_FOUND` | Dominio | No |
| `ANALYSIS_INVALID` | Análisis persistido | Sí, reanalizar |
| `MODEL_TIMEOUT` | Qwen Cloud | Sí |
| `MODEL_RATE_LIMIT` | Qwen Cloud | Sí |
| `MODEL_INVALID_JSON` | Salida estructurada | Sí, una reparación |
| `QWEN_NOT_CONFIGURED` | Configuración | No hasta configurar |
| `QWEN_TIMEOUT` | Qwen Cloud | Sí |
| `QWEN_RATE_LIMITED` | Qwen Cloud | Sí |
| `QWEN_CONNECTION_FAILED` | Qwen Cloud | Sí |
| `QWEN_INVALID_RESPONSE` | Qwen Cloud | Sí, limitado |
| `UNKNOWN_TOOL` | Orquestación | Sí, corrección |
| `TOOL_INVALID_ARGUMENT` | Tool | Sí |
| `TOOL_EXECUTION_FAILED` | Tool | Depende |
| `INSUFFICIENT_STOCK` | Regla de dominio | Sí, nueva recomendación |
| `NO_COMPATIBLE_PRODUCTS` | Regla de dominio | No automático |
| `RECOMMENDATION_INVALID` | Validación | Sí, una corrección |
| `PERSISTENCE_ERROR` | Base de datos | Sí, reintento limitado |
| `RUN_LIMIT_REACHED` | Política agentic | No automático |
| `UNEXPECTED_ERROR` | Interno | No automático |

Los códigos actuales del adaptador Qwen se conservan. La API futura podrá mapearlos a una taxonomía pública sin perder el código original seguro.

## Política de reintentos

- Qwen timeout/5xx: hasta 2 reintentos con backoff del cliente.
- Rate limit: respetar `Retry-After` cuando exista.
- JSON inválido: 1 intento de reparación.
- Tool read-only: 1 reintento si el error es transitorio.
- Recomendación inválida: 1 corrección controlada.
- Tool de escritura: usar idempotency key; no repetir a ciegas.
- Persistencia: transacción y rollback.
- Los reintentos de tools cuentan dentro del máximo de 10 ejecuciones.
- Las rondas adicionales cuentan dentro del máximo de 6.

## Estados y experiencia de error

### `completed`

- recomendación validada;
- resultado persistido;
- run cerrado;
- evento `run_completed`.

### `needs_review`

Se utiliza cuando existe valor parcial pero no puede completarse automáticamente:

- límites agotados;
- stock insuficiente sin alternativa;
- ausencia de candidatos compatibles;
- tool desconocida no corregida;
- recomendación parcial.

Debe conservar:

- resultados parciales;
- advertencias;
- razón;
- correlation ID.

### `failed`

Se utiliza cuando no existe un resultado seguro utilizable:

- salida definitivamente inválida;
- proveedor no disponible definitivamente;
- persistencia fallida;
- error interno.

Debe conservar:

- paso fallido;
- código;
- mensaje seguro;
- correlation ID;
- timestamps.

## Datos sensibles

Nunca registrar:

- API keys;
- cabeceras de autorización;
- variables de entorno completas;
- cadena de pensamiento;
- stack traces en respuestas de producto;
- datos personales innecesarios;
- respuestas completas de Qwen;
- secretos dentro de payloads de tools.

El mensaje comercial completo se conserva en la base de demo, pero los logs solo incluyen identificadores y resúmenes.

## Transacciones y consistencia

- Persistir estado y evento antes de llamar al proveedor.
- Ejecutar commit antes de la espera de red.
- No mantener una transacción de escritura SQLite abierta durante Qwen.
- Ante error, ejecutar rollback.
- Intentar registrar el fallo en una transacción nueva.
- No dejar tool executions en estado `started` después de una finalización controlada.
- Conservar secuencias ordenadas y únicas.

## Experiencia futura de UI

La UI mostrará:

- paso actual;
- estado global;
- mensaje comprensible;
- si puede reintentarse;
- resultados parciales;
- tools ejecutadas;
- reglas de validación relevantes;
- correlation ID;
- botón de reintento cuando proceda.

No mostrará:

- stack traces;
- prompts internos completos;
- cadena de pensamiento;
- credenciales;
- payloads técnicos sin resumir.

## Fuera de alcance

No se desplegarán en el MVP:

- OpenTelemetry;
- Prometheus;
- Grafana;
- ELK;
- plataforma SaaS de observabilidad;
- tracing distribuido.

Estas capacidades se revisarán cuando existan múltiples servicios, volumen operativo o requisitos formales de SRE.
