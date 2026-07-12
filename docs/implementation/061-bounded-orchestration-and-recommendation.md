# Orquestación acotada y recomendación — Sprint 2 Bloque 5

## Estado

- **Sprint:** 2 — Núcleo funcional
- **Bloque:** 5
- **Estado:** Ready for implementation
- **Rama:** `feat/sprint2-bounded-orchestration-recommendation`
- **Baseline:** `18b95f9`
- **Fecha:** 2026-07-12

## Objetivo

Implementar un orquestador único, acotado y trazable que:

1. procese una consulta comercial previamente persistida;
2. reutilice o ejecute el análisis estructurado;
3. recupere memoria del comprador cuando exista;
4. ejecute las tools de lectura aprobadas;
5. obtenga una recomendación de productos mediante Qwen Cloud;
6. valide la recomendación con reglas deterministas;
7. persista el estado del run, las ejecuciones de tools, los eventos y el resultado;
8. finalice de forma controlada ante errores o límites.

El bloque termina después de producir una recomendación validada o un resultado parcial marcado para revisión.

## Alcance incluido

Este bloque implementa exclusivamente:

- estado persistente de `agent_runs`;
- registro persistente de `tool_executions`;
- eventos funcionales de ejecución;
- `correlation_id`;
- tool registry con allowlist;
- generación de JSON Schema desde contratos Pydantic;
- ciclo acotado de function calling;
- recomendación estructurada de productos;
- validación determinista;
- errores seguros;
- límites de rondas y tools;
- logs estructurados;
- pruebas unitarias y de integración del bloque.

## Exclusiones

Este bloque no implementa:

- cotizaciones;
- `calculate_quote`;
- propuestas comerciales;
- generación de PDF;
- borradores o envío de correo;
- creación o actualización de oportunidades CRM;
- follow-up;
- escritura de memoria;
- creación automática de clientes;
- reserva o modificación de inventario;
- endpoints HTTP;
- API de runs;
- frontend;
- despliegue;
- cálculo de impuestos, transporte, aranceles o márgenes.

Las tablas existentes de oportunidades no se utilizarán como destino de escritura durante este bloque.

## Decisiones aplicables

El bloque aplica las decisiones ya aprobadas:

- ADR-005 — ciclo de tool calling controlado por backend;
- ADR-009 — observabilidad ligera;
- un solo orquestador;
- sin framework de agentes;
- sin MCP;
- sin ReAct abierto;
- sin cadena de pensamiento persistida;
- tools y dominio como fuentes de verdad;
- Qwen Cloud como componente central de selección.

No se requiere un ADR nuevo. Este documento concreta decisiones ya aceptadas.

## Arquitectura del bloque

```text
persisted inquiry
    |
    v
create agent_run
    |
    v
validate or execute inquiry analysis
    |
    v
retrieve customer history when customer_id exists
    |
    v
bounded Qwen tool loop
    |
    +--> search_catalog
    +--> get_product_details
    +--> check_stock
    |
    v
structured recommendation draft
    |
    v
deterministic validation
    |
    +--> valid ----------> completed
    |
    +--> correctable ----> one controlled correction
    |
    +--> partial --------> needs_review
    |
    +--> unrecoverable --> failed
```

## Estado del run

### Estado global

`agent_runs.status` utiliza estados gruesos y estables:

- `queued`;
- `running`;
- `completed`;
- `needs_review`;
- `failed`.

### Paso actual

`agent_runs.current_step` identifica la fase visible:

- `queued`;
- `analyzing`;
- `retrieving_memory`;
- `selecting_products`;
- `checking_stock`;
- `validating_recommendation`;
- `completed`;
- `needs_review`;
- `failed`.

El paso actual no reemplaza el estado global. Ambos campos tienen funciones distintas.

## Persistencia

### `agent_runs`

Campos previstos:

| Campo | Tipo | Regla |
|---|---|---|
| `id` | UUID/string(36) | PK |
| `inquiry_id` | UUID/string(36) | FK obligatorio |
| `correlation_id` | UUID/string(36) | único, visible en logs |
| `status` | string | estado global |
| `model` | string | modelo efectivo |
| `prompt_versions` | JSON | mapa de prompts utilizados |
| `result_payload` | JSON | recomendación validada o resultado parcial |
| `started_at` | datetime UTC | obligatorio |
| `completed_at` | datetime UTC | opcional |
| `current_step` | string | fase visible |
| `error_code` | string | opcional |
| `error_message_safe` | string | opcional |

Una inquiry puede tener varios runs. Esto permite reintentos sin sobrescribir el historial.

### `tool_executions`

Campos previstos:

| Campo | Tipo | Regla |
|---|---|---|
| `id` | UUID/string(36) | PK |
| `agent_run_id` | UUID/string(36) | FK obligatorio |
| `sequence` | integer | orden por run |
| `tool_name` | string | nombre registrado |
| `input_payload` | JSON | validado y sin secretos |
| `output_payload` | JSON | envelope serializado |
| `status` | string | `started`, `succeeded`, `failed`, `rejected` |
| `started_at` | datetime UTC | obligatorio |
| `duration_ms` | integer | >= 0 |
| `error_code` | string | opcional |

Restricción:

```text
unique(agent_run_id, sequence)
```

Cada intento de ejecución se registra y cuenta dentro del límite, incluidos rechazos y reintentos.

### `agent_run_events`

Campos previstos:

| Campo | Tipo | Regla |
|---|---|---|
| `id` | UUID/string(36) | PK |
| `agent_run_id` | UUID/string(36) | FK obligatorio |
| `sequence` | integer | orden por run |
| `event_type` | string | evento funcional |
| `step` | string | fase asociada |
| `payload` | JSON | resumen seguro |
| `created_at` | datetime UTC | obligatorio |

Restricción:

```text
unique(agent_run_id, sequence)
```

No se almacenará razonamiento interno, cadena de pensamiento ni contenido completo del proveedor.

## Eventos mínimos

El run puede registrar:

- `run_created`;
- `step_changed`;
- `analysis_reused`;
- `analysis_completed`;
- `memory_retrieval_skipped`;
- `memory_retrieved`;
- `model_round_completed`;
- `tool_requested`;
- `tool_started`;
- `tool_succeeded`;
- `tool_failed`;
- `tool_rejected`;
- `recommendation_received`;
- `recommendation_rejected`;
- `recommendation_validated`;
- `run_completed`;
- `run_needs_review`;
- `run_failed`.

Los payloads contendrán únicamente identificadores, códigos, conteos, reglas aplicadas y resúmenes seguros.

## Tool registry

El registry contiene exactamente estas tools:

1. `search_catalog`;
2. `get_product_details`;
3. `check_stock`;
4. `retrieve_customer_history`.

Cada definición registrada contiene:

- nombre estable;
- descripción para el modelo;
- modelo Pydantic de entrada;
- JSON Schema;
- ejecutor local;
- tipo de salida;
- versión;
- política de reintento.

El registry es una allowlist cerrada. El modelo nunca proporciona módulos, funciones, rutas ni código para ejecutar.

### Política de exposición

`retrieve_customer_history` se ejecuta de forma determinista antes de la selección cuando la inquiry tiene `customer_id`.

Durante el ciclo de selección se exponen a Qwen:

- `search_catalog`;
- `get_product_details`;
- `check_stock`.

El registry conserva las cuatro tools bajo un contrato común, aunque no todas deban exponerse en todas las fases.

### Errores del registry

| Condición | Código |
|---|---|
| Tool no registrada | `UNKNOWN_TOOL` |
| Argumentos no conformes | `TOOL_INVALID_ARGUMENT` |
| Error interno de ejecución | `TOOL_EXECUTION_FAILED` |
| Error de persistencia | `PERSISTENCE_ERROR` |

Una tool desconocida o inválida produce un resultado estructurado. No lanza ejecución arbitraria.

## Límites del ciclo

Constantes del MVP:

```text
MAX_MODEL_ROUNDS = 6
MAX_TOOL_EXECUTIONS = 10
MAX_READ_TOOL_RETRIES = 1
MAX_RECOMMENDATION_CORRECTIONS = 1
```

Reglas:

- cada llamada lógica a Qwen incrementa las rondas;
- cada intento de tool incrementa las ejecuciones;
- varias tool calls en una respuesta se ejecutan en el orden recibido;
- no se inicia una ejecución si excedería el límite;
- al alcanzar el límite, el run termina como `needs_review`;
- no existe un bucle abierto;
- no existe recursión agentic.

## Transacciones y llamadas externas

No se mantiene una transacción de escritura SQLite abierta durante una llamada a Qwen Cloud.

Patrón obligatorio:

```text
persist state/event
commit
call provider
validate response
persist next state/event
commit
```

Las tools de lectura utilizan sesiones controladas y no modifican catálogo, stock ni memoria.

Si falla una escritura de trazabilidad:

- se ejecuta rollback;
- el run se intenta marcar como `failed` mediante una transacción nueva;
- no se exponen excepciones SQLAlchemy al modelo ni al usuario.

## Entrada del orquestador

Entrada mínima:

```text
inquiry_id
```

El orquestador carga desde persistencia:

- mensaje original;
- customer asociado;
- análisis estructurado;
- campos faltantes;
- idioma;
- mercado;
- producto de interés;
- volumen estimado;
- canal;
- horizonte o fecha;
- presupuesto cuando exista;
- requisitos de certificación.

## Reutilización del análisis

El análisis existente se reutiliza únicamente cuando:

1. `inquiries.extracted_data` no está vacío;
2. valida nuevamente contra `InquiryAnalysis`;
3. la versión del esquema es compatible;
4. el status no representa un fallo incompatible.

Si no cumple estas condiciones, se ejecuta `InquiryAnalysisService`.

La reutilización se registra mediante `analysis_reused`.

## Recuperación de memoria

Cuando existe `customer_id`:

- se invoca `retrieve_customer_history`;
- se conservan solo memorias activas;
- el resultado se registra como tool execution;
- el contexto resumido se entrega al modelo.

Cuando no existe `customer_id`:

- no se crea un cliente;
- no se invoca la tool;
- se registra `memory_retrieval_skipped`;
- el flujo puede continuar sin memoria.

La creación de clientes pertenece a un bloque posterior.

## Prompt de recomendación

Se crea:

```text
product_recommendation.v1
```

El prompt recibe:

- mensaje original;
- análisis validado;
- campos faltantes;
- memoria relevante;
- resultados de tools;
- política de no invención;
- reglas del formato final.

El modelo puede solicitar únicamente las tools expuestas para la fase.

## Borrador de recomendación

La salida del modelo se valida con un esquema Pydantic:

```json
{
  "schema_version": "1.0",
  "items": [
    {
      "product_id": "uuid",
      "quantity_bottles": 300,
      "rationale": "Suitable for specialised German wine shops."
    }
  ],
  "summary": "Two Albariño references suitable for the requested channel.",
  "warnings": []
}
```

El modelo no devuelve como autoridad:

- SKU;
- nombre oficial;
- precio;
- moneda;
- stock vendible;
- unidades por caja;
- número de cajas;
- certificaciones;
- disponibilidad.

Esos valores se incorporan desde catálogo y stock después de validar los IDs.

## Resultado validado

El resultado persistido puede incluir:

```json
{
  "schema_version": "1.0",
  "items": [
    {
      "product_id": "uuid",
      "sku": "ADA-ALB-JOV-2025",
      "name": "Brétema Albariño 2025",
      "quantity_bottles": 300,
      "units_per_case": 6,
      "cases": 50,
      "unit_price_cents": 840,
      "sellable_bottles": 1200,
      "rationale": "Suitable for specialised German wine shops."
    }
  ],
  "total_bottles": 600,
  "currency": "EUR",
  "summary": "Validated product recommendation.",
  "warnings": [],
  "validation_status": "valid"
}
```

No incluye subtotal ni total monetario. Esos cálculos pertenecen al bloque de cotización.

## Aplicación limitada del presupuesto

Cuando existen:

- `budget_total_cents`;
- `budget_currency == "EUR"`;
- `estimated_bottles`;

se puede derivar de forma determinista:

```text
max_unit_price_cents = budget_total_cents // estimated_bottles
```

Ese valor puede utilizarse como filtro conservador de `search_catalog`.

No se calcula un presupuesto mixto, conversión de moneda ni cotización.

Cuando la moneda no sea EUR o falte:

- el presupuesto no se aplica;
- se añade la advertencia `BUDGET_NOT_APPLIED`;
- el run no inventa una tasa de cambio.

## Validación determinista

Una recomendación es válida únicamente cuando se cumplen todas las reglas aplicables.

### Identidad del producto

- todos los IDs existen;
- todos los productos están activos;
- no existen IDs duplicados;
- todos los productos fueron obtenidos mediante tools durante el run;
- SKU, nombre, precio y certificaciones coinciden con catálogo.

### Cantidades

- cada cantidad es mayor que cero;
- cada cantidad es divisible por `units_per_case`;
- `cases = quantity_bottles // units_per_case`;
- si existe `estimated_bottles`, la suma debe coincidir exactamente;
- no se aceptan cantidades implícitas ni negativas.

### Stock

- `check_stock` debe haberse ejecutado para cada producto;
- el requested volume debe coincidir con la recomendación;
- `available` debe ser verdadero;
- `shortfall` debe ser cero;
- el stock nunca se reserva ni modifica.

### Mercado y canal

La recomendación debe estar respaldada por:

- coincidencia de mercado;
- coincidencia de canal;
- coincidencia de producto o variedad;
- o una justificación explícita basada en datos de catálogo.

Una ausencia de coincidencia directa produce una advertencia o rechazo según la severidad.

### Certificaciones

Cuando la consulta exige certificaciones:

- cada certificación afirmada debe existir en el producto;
- una certificación ausente no puede inferirse;
- si no hay candidatos compatibles, el resultado pasa a `needs_review`.

### Datos no vinculantes

El modelo puede redactar:

- rationale;
- summary;
- warnings.

El backend determina:

- identidad;
- cantidades válidas;
- stock;
- cajas;
- precio oficial;
- moneda;
- certificaciones existentes.

## Corrección controlada

Cuando el borrador falla reglas corregibles:

1. se genera una lista estructurada de errores;
2. se entrega al modelo junto con los resultados verificados;
3. se permite una sola corrección;
4. se vuelve a validar desde cero.

No se corrige silenciosamente una selección del modelo.

Errores corregibles:

- suma de cantidades incorrecta;
- cantidades no divisibles por caja;
- producto duplicado;
- producto sin stock;
- selección fuera del conjunto recuperado.

Errores no corregibles automáticamente:

- persistencia fallida;
- proveedor no disponible después de reintentos;
- ausencia total de candidatos;
- límite de rondas o tools agotado.

## Estados terminales

| Condición | Estado |
|---|---|
| Recomendación validada | `completed` |
| Recomendación parcial útil | `needs_review` |
| Stock insuficiente sin alternativa | `needs_review` |
| No existen candidatos compatibles | `needs_review` |
| Límite alcanzado | `needs_review` |
| Tool desconocida no corregida | `needs_review` |
| JSON inválido después de corrección | `failed` |
| Error definitivo de Qwen | `failed` |
| Error de persistencia | `failed` |
| Error interno inesperado | `failed` |

## Códigos de error

El bloque puede producir:

- `INQUIRY_NOT_FOUND`;
- `ANALYSIS_INVALID`;
- `UNKNOWN_TOOL`;
- `TOOL_INVALID_ARGUMENT`;
- `TOOL_EXECUTION_FAILED`;
- `INSUFFICIENT_STOCK`;
- `NO_COMPATIBLE_PRODUCTS`;
- `RECOMMENDATION_INVALID`;
- `RUN_LIMIT_REACHED`;
- `QWEN_NOT_CONFIGURED`;
- `QWEN_TIMEOUT`;
- `QWEN_RATE_LIMITED`;
- `QWEN_CONNECTION_FAILED`;
- `QWEN_INVALID_RESPONSE`;
- `PERSISTENCE_ERROR`;
- `UNEXPECTED_ERROR`.

Los mensajes persistidos deben ser seguros y no incluir stack traces, credenciales ni payloads sensibles completos.

## Logs

Los logs JSON incluirán cuando aplique:

```json
{
  "correlation_id": "uuid",
  "agent_run_id": "uuid",
  "event": "tool_completed",
  "step": "checking_stock",
  "tool": "check_stock",
  "duration_ms": 14,
  "error_code": null
}
```

No se registrarán:

- API keys;
- variables de entorno completas;
- cabeceras de autorización;
- cadena de pensamiento;
- respuesta completa del proveedor;
- mensaje comercial completo en cada evento.

## Protocolos de proveedor

El orquestador depende de protocolos pequeños y sustituibles para:

- function calling;
- structured JSON completion.

Las pruebas utilizan clientes falsos. Las pruebas unitarias no llaman Qwen Cloud.

La integración live continúa separada y no se ejecuta dentro de la suite normal.

## Archivos previstos

```text
apps/api/alembic/versions/0002_agent_run_traceability.py

apps/api/app/agent/registry.py
apps/api/app/agent/orchestrator.py

apps/api/app/domain/recommendation.py
apps/api/app/repositories/agent_runs.py
apps/api/app/services/recommendation_validation.py

apps/api/app/ai/prompts/product_recommendation.v1.md

apps/api/tests/test_agent_run_migration.py
apps/api/tests/test_tool_registry.py
apps/api/tests/test_recommendation_validation.py
apps/api/tests/test_bounded_orchestration.py
```

La distribución exacta puede ajustarse si simplifica el código sin alterar los contratos.

## Pruebas requeridas

### Persistencia

- upgrade de migración;
- downgrade de migración;
- creación de run;
- múltiples runs para una inquiry;
- secuencia única de events;
- secuencia única de tool executions;
- persistencia de resultado;
- persistencia de error seguro.

### Registry

- allowlist exacta;
- JSON Schema correcto;
- ejecución de cada tool;
- rechazo de tool desconocida;
- rechazo de argumentos inválidos;
- envelope común;
- ausencia de ejecución arbitraria.

### Validación

- recomendación válida de 600 botellas;
- exactamente dos referencias en el escenario principal;
- suma incorrecta;
- cantidad incompatible con caja;
- producto duplicado;
- producto no recuperado;
- producto inexistente;
- stock insuficiente;
- certificación inexistente;
- resultado enriquecido desde catálogo;
- ausencia de subtotal o quote.

### Orquestación

- reutilización del análisis;
- ejecución de análisis cuando falta;
- recuperación de memoria;
- skip de memoria sin customer;
- tools registradas en orden;
- máximo seis rondas;
- máximo diez ejecuciones;
- una corrección controlada;
- timeout seguro;
- tool desconocida;
- finalización `completed`;
- finalización `needs_review`;
- finalización `failed`;
- no mantener transacción durante llamada externa.

## Escenario principal del bloque

Dada una consulta del comprador alemán con:

- mercado `DE`;
- canal `specialty_retail`;
- interés en Albariño;
- 600 botellas;
- solicitud de dos referencias;
- muestras solicitadas;
- presupuesto desconocido;

el resultado esperado es:

- memoria recuperada;
- catálogo consultado;
- detalles consultados;
- stock consultado;
- dos productos activos;
- cantidades que suman 600;
- cantidades divisibles por caja;
- stock suficiente;
- precio y SKU provenientes del catálogo;
- recomendación persistida;
- run `completed`;
- eventos y tool executions persistidos;
- ausencia de quote, oportunidad nueva, seguimiento o artefactos.

La selección concreta no se hardcodea en el orquestador. Debe derivarse del catálogo, el canal, el mercado, el volumen y el stock.

## Criterios de aceptación

El bloque se acepta cuando:

1. existe una migración reversible para trazabilidad;
2. el registry contiene únicamente las cuatro tools aprobadas;
3. una tool desconocida nunca se ejecuta;
4. el ciclo respeta seis rondas y diez ejecuciones;
5. el escenario principal produce una recomendación válida;
6. una recomendación con stock insuficiente no termina como válida;
7. los datos comerciales autoritativos provienen de tools;
8. la recomendación queda persistida en `agent_runs.result_payload`;
9. events y tool executions conservan orden;
10. no se persiste cadena de pensamiento;
11. Ruff pasa;
12. mypy strict pasa;
13. pytest pasa;
14. cobertura permanece por encima del umbral configurado;
15. no se implementan capacidades excluidas.

## Riesgos

### El modelo omite tools necesarias

Mitigación:

- fases obligatorias controladas por backend;
- validación que exige evidencia de catálogo y stock.

### El modelo repite tools

Mitigación:

- límites;
- conteo de ejecuciones;
- resultados previos disponibles en contexto.

### El modelo inventa datos de producto

Mitigación:

- el borrador solo acepta IDs, cantidades y texto explicativo;
- el backend enriquece desde catálogo.

### Payloads de trazabilidad demasiado grandes

Mitigación:

- registrar envelopes resumidos;
- no almacenar respuestas completas del proveedor.

### SQLite bloqueado por llamadas externas

Mitigación:

- commits antes de cada llamada a Qwen;
- ninguna transacción de escritura abierta durante espera de red.

### Recomendación demasiado acoplada al escenario demo

Mitigación:

- reglas generales;
- datos semilla separados;
- ningún ID o reparto de cantidades hardcodeado en producción.

## Definition of Done del bloque

- documentación aprobada;
- migración reversible;
- modelos SQLAlchemy;
- repositorio de runs;
- registry tipado;
- prompt versionado;
- contratos de recomendación;
- validador determinista;
- orquestador acotado;
- trazabilidad persistida;
- errores seguros;
- tests del bloque;
- README y verification actualizados;
- `make check-api` en verde;
- ningún secreto;
- ningún cambio de API o frontend.

## Orden de implementación

1. actualizar documentación canónica;
2. implementar migración y modelos;
3. implementar repositorio de trazabilidad;
4. implementar registry;
5. implementar contratos de recomendación;
6. implementar validación determinista;
7. implementar ciclo acotado;
8. añadir pruebas de integración;
9. actualizar README, changelog y verification;
10. ejecutar verificación combinada.

No se inicia el paso 2 hasta revisar el diff documental.
