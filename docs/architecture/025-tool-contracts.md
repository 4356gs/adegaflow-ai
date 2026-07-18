# Contratos de herramientas y capacidades

## Convención común

Toda tool devuelve:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "tool_version": "1.0",
    "duration_ms": 12
  }
}
```

En error:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "Safe human-readable message",
    "retryable": false
  },
  "meta": {
    "tool_version": "1.0",
    "duration_ms": 4
  }
}
```

## Reglas

- entradas y salidas se validan con Pydantic;
- no se exponen excepciones internas;
- las tools son idempotentes cuando sea posible;
- las tools de escritura aceptan `idempotency_key`;
- cada ejecución se registra;
- precios en céntimos;
- fechas en ISO 8601;
- no se incluyen secretos en logs.

Las capacidades del Bloque 6 no se incorporan al tool registry expuesto a Qwen.
`calculate_quote` es determinista y `generate_proposal`/`draft_email` son
servicios de aplicación con prompts estructurados.

Las acciones internas del Bloque 7 tampoco se incorporan a la allowlist
seleccionable por Qwen. El orquestador las invoca en orden, registra cada
intento como tool execution y aplica ADR-013.

---

## `search_catalog` — P0

### Propósito

Buscar productos por variedad, categoría, mercado, rango de precio y canal.

### Entrada

```json
{
  "query": "Albariño",
  "market": "DE",
  "channel": "specialty_retail",
  "max_unit_price_cents": null,
  "limit": 5
}
```

### Salida

Lista resumida de candidatos con `product_id`, SKU, nombre, categoría, precio y razones de coincidencia.

---

## `get_product_details` — P0

### Entrada

```json
{
  "product_ids": ["uuid-1", "uuid-2"]
}
```

### Salida

Ficha completa de cada producto, sin datos de inventario.

---

## `check_stock` — P0

### Entrada

```json
{
  "items": [
    {
      "product_id": "uuid-1",
      "requested_bottles": 300
    }
  ]
}
```

### Salida

```json
{
  "items": [
    {
      "product_id": "uuid-1",
      "requested_bottles": 300,
      "sellable_bottles": 720,
      "available": true,
      "shortfall": 0
    }
  ]
}
```

---

## `calculate_quote` — P0

Capacidad interna determinista; no seleccionable por Qwen.

### Entrada

```json
{
  "agent_run_id": "uuid"
}
```

### Salida

```json
{
  "quote_id": "uuid",
  "agent_run_id": "uuid",
  "currency": "EUR",
  "items": [
    {
      "product_id": "uuid-1",
      "quantity_bottles": 300,
      "unit_price_cents": 1400,
      "line_total_cents": 420000,
      "cases": 50
    }
  ],
  "subtotal_cents": 420000,
  "assumptions": [
    "taxes_excluded",
    "shipping_excluded",
    "duties_excluded",
    "stock_not_reserved"
  ],
  "status": "draft"
}
```

Los productos, cantidades, precios y unidades por caja proceden de la
recomendación validada. Las cantidades deben ser divisibles por caja, de acuerdo
con la validación del Bloque 5. No calcula impuestos, transporte, seguros,
aranceles, descuentos, margen ni conversiones.

---

## `retrieve_customer_history` — P0

### Entrada

```json
{
  "customer_id": "uuid",
  "categories": ["preference", "interaction", "constraint"],
  "limit": 20
}
```

### Salida

Memorias activas y resumen de oportunidades anteriores.

---

## `save_customer_memory` — P0

### Entrada

```json
{
  "customer_id": "uuid",
  "memories": [
    {
      "category": "preference",
      "content": "Interested in Albariño for specialised retail in Germany.",
      "confidence": 0.92,
      "source_inquiry_id": "uuid"
    }
  ],
  "idempotency_key": "run-uuid:save_customer_memory"
}
```

### Reglas

- no guardar inferencias sensibles;
- no duplicar hechos equivalentes;
- máximo 20 hechos explícitos;
- omitir dirección, contacto, identificador fiscal y presupuesto;
- permitir invalidación posterior;
- usar un receipt y fingerprint para idempotencia de lote.

---

## `create_crm_opportunity` — P0

### Entrada

```json
{
  "inquiry_id": "uuid",
  "customer_id": "uuid",
  "title": "German specialty retail — 600 bottles",
  "priority": "high",
  "score": 82,
  "market": "DE",
  "channel": "specialty_retail",
  "estimated_bottles": 600,
  "target_date": "2026-09-08",
  "summary": "Qualified B2B import opportunity.",
  "idempotency_key": "run-uuid:create_crm_opportunity"
}
```

### Salida

`opportunity_id`, etapa, prioridad, score y timestamp. Stage, score, prioridad,
título y resumen se construyen mediante reglas deterministas; Qwen no los
proporciona.

---

## `update_crm_opportunity` — P1

Permite cambiar etapa, prioridad o resumen. No es necesaria para el camino feliz inicial.

---

## `create_followup_task` — P0

### Entrada

```json
{
  "opportunity_id": "uuid",
  "title": "Follow up on samples and pricing",
  "due_at": "2026-07-17T15:00:00Z",
  "idempotency_key": "run-uuid:create_followup_task"
}
```

El vencimiento usa un reloj UTC inyectable y se fija a siete días naturales. No
se crea una entrada de calendario ni una notificación externa.

---

## `generate_proposal` — P0

Servicio de aplicación con salida estructurada; no seleccionable por Qwen.

### Entrada

```json
{
  "agent_run_id": "uuid",
  "quote_id": "uuid",
  "language": "en",
  "include_assumptions": true
}
```

### Salida

Artefacto versionado con narrativa validada y secciones comerciales ensambladas
por el backend. Incluye comprador conocido, productos, cantidades, precios,
subtotal, supuestos, exclusiones, próximos pasos y advertencias.

Se persiste con `review_status=needs_review`. HTML final y PDF quedan fuera del
Bloque 6.

---

## `draft_email` — P0

Servicio de aplicación con salida estructurada; no seleccionable por Qwen.

### Entrada

```json
{
  "agent_run_id": "uuid",
  "quote_id": "uuid",
  "proposal_artifact_id": "uuid",
  "language": "en",
  "tone": "professional_concise"
}
```

### Salida

Asunto, secciones de cuerpo, resumen comercial determinista, preguntas de
clarificación, llamada a la acción, advertencias y estado `needs_review`.

No envía correo ni afirma aprobación, reserva de stock o inclusión de conceptos
excluidos.

---

## `translate_message` — P1

No se utilizará en el camino feliz porque Qwen puede generar directamente en el idioma objetivo. Se conserva como capacidad futura cuando sea necesario preservar una traducción independiente.
