# Estrategia de pruebas del Sprint 2

## Objetivo

Probar reglas deterministas de forma exhaustiva y aislar la variabilidad del modelo.

## Pirámide

### Unitarias

Cubren:

- schemas;
- cálculo de cotización;
- reglas de stock;
- scoring;
- normalización de memoria;
- idempotencia;
- tool handlers;
- transición de estados.

No llaman a Qwen Cloud.

### Contrato

Cubren:

- JSON Schema de tools;
- serialización de mensajes;
- parsing de tool calls;
- salida Pydantic;
- errores API.

### Integración

Cubren:

- repositorios con SQLite temporal;
- migraciones;
- seed loader;
- tool registry;
- orquestador con cliente Qwen falso;
- transacciones;
- endpoints FastAPI.

### Live Qwen

Marcadas `live_qwen`.

Cubren:

- disponibilidad;
- JSON mode;
- function calling;
- roundtrip.

No se ejecutan en CI por defecto porque consumen cuota y requieren secreto.

### End-to-end backend

Desde `POST /inquiries` hasta la oportunidad, propuesta, seguimiento y memoria.

## Dobles de prueba

### `FakeQwenClient`

Respuestas deterministas por fase:

- análisis;
- tool call;
- recomendación;
- redacción.

### `ScriptedQwenClient`

Secuencia configurable para probar:

- múltiples tools;
- argumentos inválidos;
- timeout;
- salida inválida;
- agotamiento de rondas.

## Casos críticos

- stock nunca negativo;
- total de cotización correcto;
- productos recomendados activos;
- no duplicar oportunidad;
- no duplicar seguimiento;
- memoria recuperable;
- no almacenar secretos;
- fallo del modelo deja run en estado consistente;
- retry no duplica escrituras.

## Comandos esperados

```bash
pytest
pytest -m "not live_qwen"
pytest -m live_qwen
ruff check .
mypy app
```

## Umbrales

- 100 % de reglas monetarias y de stock cubiertas.
- Cobertura global objetivo: 80 % o superior.
- Todos los escenarios P0 pasan.
- Test live no bloquea CI, pero debe ejecutarse antes del cierre.
- Ningún test depende del orden de ejecución.

La cobertura es una señal, no sustituto de los casos de aceptación.
