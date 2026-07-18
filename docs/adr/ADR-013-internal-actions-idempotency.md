# ADR-013: Acciones internas deterministas e idempotentes

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-18
- **Decisores:** Equipo técnico AdegaFlow AI
- **Relacionados:** ADR-005, ADR-006, ADR-007, ADR-009, ADR-012

## Contexto

El Sprint 2 Bloque 7 debe crear una oportunidad CRM simulada, una tarea de
seguimiento y memoria comercial después de persistir una cotización y sus dos
artefactos. Las tres acciones escriben únicamente en SQLite, pero deben ser
repetibles, auditables y seguras ante reintentos.

El modelo vigente ya contiene `opportunities` y `customer_memories`, pero no
contiene `follow_up_tasks` ni un mecanismo persistente común para las claves de
idempotencia. Además, una inquiry puede no tener `customer_id`, aunque
`opportunities.customer_id` es obligatorio.

Bloque 6 termina en `needs_review`. Bloque 7 debe añadir acciones internas sin
aprobar los artefactos, enviar comunicaciones, reservar inventario ni depender
de otra respuesta de Qwen.

## Decisión

### 1. Límite de la fase

Las acciones internas se ejecutan solo cuando el run posee:

- recomendación validada;
- una cotización persistida;
- una propuesta persistida;
- un borrador de correo persistido;
- ambos artefactos con `review_status=needs_review`.

Un resultado parcial del Bloque 6 se conserva en `needs_review` y no intenta
acciones internas.

### 2. Ejecución controlada por el backend

`create_crm_opportunity`, `create_followup_task` y `save_customer_memory` serán
capacidades internas tipadas invocadas en orden por el orquestador.

- no se añaden al conjunto de tools seleccionables por Qwen;
- cada capacidad valida entrada y salida con Pydantic;
- cada intento se registra como `tool_execution` y mediante eventos funcionales;
- no se realiza ninguna llamada adicional al modelo;
- los campos autoritativos se derivan de datos persistidos y validados.

### 3. Propiedad

- la oportunidad pertenece a la inquiry mediante `unique(inquiry_id)`;
- la procedencia del run se conserva en ejecuciones y eventos, sin añadir una
  FK obligatoria desde la oportunidad al run;
- la tarea pertenece a la oportunidad;
- cada memoria pertenece al customer y conserva `source_inquiry_id`;
- cotización y artefactos siguen relacionados con la oportunidad mediante la
  inquiry compartida, según ADR-012.

No se añade un agregado CRM ni un `commercial_package`.

### 4. Resolución del comprador

El orden es determinista:

1. reutilizar `inquiry.customer_id` cuando referencia un customer existente;
2. si no existe, crear un customer mínimo únicamente cuando el análisis
   validado contiene `company_name` y `market`;
3. utilizar `contact_name` y `contact_email` solo cuando estén presentes;
4. usar el idioma validado de la inquiry y fallback `en`;
5. asociar el nuevo customer a la inquiry dentro de la misma transacción.

No se intenta fusionar compradores por nombre o email en el Bloque 7. Si faltan
empresa o mercado, no se inventa identidad: las acciones se rechazan de forma
segura y el run permanece `needs_review`.

### 5. Calificación determinista

Qwen no decide `score`, `priority` ni `stage`.

El score se limita a 0-100 y suma:

| Evidencia validada | Puntos |
|---|---:|
| intención `b2b_purchase_inquiry` | 40 |
| intención `price_request` o `sample_request` | 30 |
| intención `product_information` | 20 |
| otra intención | 10 |
| customer resuelto o empresa identificada | 10 |
| mercado | 10 |
| volumen estimado | 10 |
| canal | 10 |
| fecha u horizonte objetivo | 10 |
| presupuesto EUR conocido | 5 |
| email de contacto | 5 |

El resultado se trunca a 100. La prioridad es:

- `low`: 0-49;
- `medium`: 50-74;
- `high`: 75-100.

La etapa inicial es `proposal_draft`. Título y resumen se construyen con
plantillas deterministas a partir de empresa, mercado, volumen, canal y resumen
de la recomendación. No se copian importes al registro CRM.

### 6. Seguimiento

El seguimiento estándar se crea para siete días naturales después del instante
de ejecución:

```text
due_at = utc_now + 7 days
```

El reloj se inyecta para que las pruebas sean reproducibles. El título se
construye de forma determinista y el estado inicial es `pending`.

### 7. Memoria permitida

Se guardan como máximo 20 hechos explícitos derivados del análisis validado:

- intereses de producto como `preference`;
- mercado y canal como `preference`;
- certificaciones y condiciones de entrega como `requirement`;
- solicitud de muestras o lista de precios como `interaction`.

Cada hecho conserva `source_inquiry_id`, `confidence=1.0` como indicador de que
procede de un campo explícito validado, y `is_active=true`.

No se guardan dirección de muestras, email, teléfono, identificador fiscal,
presupuesto, inferencias sensibles ni texto generado por los artefactos. Los
hechos se normalizan y deduplican por customer, categoría, contenido
normalizado e inquiry fuente.

### 8. Idempotencia persistente

La migración del Bloque 7 añade `internal_action_receipts` con:

- `id`;
- `agent_run_id`;
- `action_name`;
- `idempotency_key`, único;
- `request_fingerprint`;
- `result_payload`, con referencias resumidas;
- `created_at`.

Las claves canónicas son:

```text
{agent_run_id}:create_crm_opportunity
{agent_run_id}:create_followup_task
{agent_run_id}:save_customer_memory
```

El fingerprint se calcula sobre el payload canónico validado, nunca sobre
objetos no normalizados.

- misma clave y mismo fingerprint: devolver el resultado persistido;
- misma clave y fingerprint distinto: `IDEMPOTENCY_CONFLICT`;
- una clave no se reutiliza entre acciones;
- el receipt y las entidades creadas se confirman en la misma transacción.

`tool_executions` conserva todos los intentos y no se usa como tabla de
idempotencia porque su propósito es auditoría secuencial.

### 9. Atomicidad

Comprador nuevo, asociación de la inquiry, oportunidad, seguimiento, memorias y
receipts se escriben en una sola transacción SQLite.

Antes de abrirla, el orquestador persiste el cambio a `persisting_actions` y los
eventos de inicio. No se realizan llamadas de red dentro de la transacción.

Si una escritura falla:

- se revierte toda la unidad de acciones;
- no quedan oportunidad, seguimiento o memorias parciales;
- se conserva la cotización y los artefactos del Bloque 6;
- si la base permite registrar el resultado, el run queda `needs_review` con
  un error seguro y reintentable;
- un fallo que impida persistir el propio estado se propaga como error de
  infraestructura sin afirmar que las acciones se completaron.

### 10. Estado final

El camino feliz termina nuevamente en:

```text
status = needs_review
current_step = needs_review
```

Las acciones internas no equivalen a aprobación humana. `result_payload` añade
solo referencias a customer, oportunidad, seguimiento y memorias; no duplica
las entidades completas.

## Alternativas consideradas

### Permitir que Qwen seleccione y redacte las escrituras

Descartada porque introduce variabilidad en score, fechas, memoria e
idempotencia sin aportar valor al flujo del hackathon.

### Añadir `idempotency_key` a cada entidad

Descartada porque una ejecución de `save_customer_memory` puede producir varios
registros y no posee una correspondencia uno a uno entre clave y fila.

### Usar solamente restricciones de dominio

`unique(inquiry_id)` evita dos oportunidades, pero no detecta que la misma clave
llegó con otro contenido y no cubre de forma uniforme seguimiento y memoria.

### Usar `tool_executions` como ledger

Descartada porque los reintentos deben conservarse como intentos separados. Una
restricción única por clave eliminaría evidencia de auditoría.

### Persistir cada acción en una transacción independiente

Descartada para el MVP porque aumenta los estados parciales y complica AT-010.
No existe una integración externa que obligue a una saga.

## Consecuencias

### Positivas

- resultados reproducibles sin nuevas llamadas al modelo;
- reintentos seguros y conflictos detectables;
- una sola frontera transaccional;
- memoria explícita y auditable;
- trazabilidad compatible con la futura interfaz;
- conserva el control humano sobre propuesta y correo.

### Negativas

- una tabla adicional para receipts;
- la transacción incluye varias escrituras relacionadas;
- no se fusionan automáticamente compradores duplicados;
- el scoring es una política MVP, no un modelo comercial validado.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| memoria duplicada | normalización, deduplicación y receipt |
| dos compradores para la misma empresa | no hacer matching implícito; asociación explícita posterior |
| reintento con datos distintos | fingerprint y conflicto seguro |
| fecha no reproducible | reloj UTC inyectable |
| transacción parcial | una única unidad y rollback |
| score presentado como verdad | regla visible, determinista y limitada al demo |

## Condición de revisión

Revisar esta decisión si se incorpora:

- CRM real;
- más de un seguimiento automático por oportunidad;
- aprobación humana antes de escribir CRM;
- matching real de compradores;
- procesamiento concurrente con múltiples workers;
- PostgreSQL o una cola durable;
- memoria editable desde la interfaz.
