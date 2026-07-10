# Spike técnico de Qwen Cloud

## Objetivo

Reducir el mayor riesgo técnico antes de construir el dominio: confirmar que la cuenta y el endpoint disponibles ejecutan de forma estable JSON Object mode y function calling con `qwen3.7-plus`.

## Entregables del spike

```text
scripts/qwen_spike/
├── 01_basic_call.py
├── 02_structured_output.py
├── 03_single_tool_call.py
├── 04_tool_roundtrip.py
├── 05_error_handling.py
├── README.md
└── results.md
```

Estos scripts son exploratorios y no se importan desde el código de producción.

## Configuración

```text
DASHSCOPE_API_KEY
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.7-plus
QWEN_FALLBACK_MODEL=qwen3.6-flash
QWEN_TIMEOUT_SECONDS=30
```

## Experimentos

### S-01 — Llamada básica

**Entrada:** una instrucción breve en inglés.  
**Esperado:** respuesta válida, uso de tokens y modelo efectivo.

### S-02 — Salida estructurada

**Entrada:** mensaje comercial.  
**Configuración:** `response_format={"type":"json_object"}` y prompt que exige JSON.  
**Esperado:** JSON parseable.

Validaciones:

- intención;
- idioma;
- mercado;
- volumen;
- canal;
- fecha objetivo;
- muestras;
- campos faltantes.

El JSON se valida con Pydantic porque JSON Object mode no garantiza conformidad semántica con el schema.

### S-03 — Selección de una tool

Registrar una única tool ficticia `search_catalog`.

**Esperado:**

- `finish_reason=tool_calls`;
- nombre permitido;
- argumentos JSON;
- parámetros conformes.

### S-04 — Roundtrip

1. modelo solicita `search_catalog`;
2. aplicación ejecuta una función local;
3. resultado vuelve como mensaje `tool`;
4. modelo genera respuesta final basada en los resultados.

### S-05 — Argumento inválido

La tool rechaza una entrada. El resultado de error vuelve al modelo.

**Esperado:** corrección o respuesta segura; no excepción sin controlar.

### S-06 — Timeout o credencial inválida

**Esperado:** clasificación del error, mensaje seguro y run fallido.

### S-07 — Comparación de modelos

Ejecutar el caso de análisis tres veces con:

- `qwen3.7-plus`;
- `qwen3.6-flash`.

Registrar:

- validez JSON;
- exactitud de campos;
- latencia;
- tokens;
- coste estimado cuando esté disponible.

## Criterios de aprobación

- 3 de 3 salidas JSON parseables por modelo principal.
- 3 de 3 tool calls con nombre y argumentos válidos.
- roundtrip completo sin intervención manual.
- error de credencial o timeout clasificado.
- latencia mediana del roundtrip por debajo de 15 segundos en el entorno de prueba.
- ningún secreto en scripts o resultados.

El umbral de latencia es un criterio interno, no una promesa de proveedor.

## Decisión posterior

- **Aprueba:** continuar con el cliente Qwen de producción.
- **Aprueba con reservas:** reducir rondas, usar fallback o simplificar prompt.
- **Falla:** detener Sprint 2 y resolver integración antes de crear tools reales.
