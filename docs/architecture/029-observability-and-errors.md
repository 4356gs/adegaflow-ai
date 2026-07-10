# Observabilidad y manejo de errores

## Objetivos

1. Entender qué ocurrió durante una ejecución.
2. Mostrar trazabilidad útil al usuario.
3. Diagnosticar fallos sin exponer secretos.
4. Medir latencia y estabilidad de la demo.

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
  "tool": "check_stock",
  "duration_ms": 14
}
```

### Trazabilidad funcional

Persistida en:

- `agent_runs`;
- `tool_executions`;
- eventos de estado.

Es la fuente para la interfaz.

### Métricas mínimas derivadas

- duración total del run;
- duración por tool;
- número de llamadas a Qwen;
- número de tools;
- reintentos;
- estado final;
- tokens si el proveedor los devuelve;
- causa de fallo.

No se desplegará Prometheus para el MVP.

## Taxonomía de errores

| Código | Tipo | Recuperable |
|---|---|---:|
| `INVALID_INPUT` | Entrada de usuario | No, requiere corrección |
| `MODEL_TIMEOUT` | Qwen Cloud | Sí |
| `MODEL_RATE_LIMIT` | Qwen Cloud | Sí |
| `MODEL_INVALID_JSON` | Salida estructurada | Sí, una reparación |
| `UNKNOWN_TOOL` | Orquestación | Sí, corrección |
| `TOOL_INVALID_ARGUMENT` | Tool | Sí |
| `TOOL_EXECUTION_FAILED` | Tool | Depende |
| `INSUFFICIENT_STOCK` | Regla de dominio | Sí, nueva recomendación |
| `PERSISTENCE_ERROR` | Base de datos | Sí, reintento limitado |
| `RUN_LIMIT_REACHED` | Política agentic | No automático |
| `UNEXPECTED_ERROR` | Interno | No automático |

## Política de reintentos

- Qwen timeout/5xx: hasta 2 reintentos con backoff.
- Rate limit: respetar `Retry-After` cuando exista.
- JSON inválido: 1 intento de reparación.
- Tool read-only: 1 reintento si el error es transitorio.
- Tool de escritura: usar idempotency key; no repetir a ciegas.
- Persistencia: transacción y rollback.

## Datos sensibles

Nunca registrar:

- API keys;
- cabeceras de autorización;
- variables de entorno completas;
- cadena de pensamiento;
- datos personales innecesarios.

El mensaje comercial completo se conserva en la base de demo, pero los logs solo incluirán identificadores y resúmenes.

## Experiencia de error

La UI mostrará:

- paso fallido;
- mensaje comprensible;
- si puede reintentarse;
- resultados parciales;
- correlation ID;
- botón de reintento cuando proceda.

No mostrará stack traces.
