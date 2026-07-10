# Contratos de herramientas

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

### Entrada

```json
{
  "currency": "EUR",
  "items": [
    {
      "product_id": "uuid-1",
      "quantity_bottles": 300
    }
  ]
}
```

### Salida

Importes por línea, subtotal, cajas, unidades sobrantes y supuestos. No calcula impuestos, transporte ni aduanas.

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
  "idempotency_key": "run-uuid-save-memory"
}
```

### Reglas

- no guardar inferencias sensibles;
- no duplicar hechos equivalentes;
- permitir invalidación posterior.

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
  "idempotency_key": "run-uuid-create-opportunity"
}
```

### Salida

`opportunity_id`, etapa y timestamp.

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
  "idempotency_key": "run-uuid-followup"
}
```

---

## `generate_proposal` — P0

### Entrada

```json
{
  "opportunity_id": "uuid",
  "quote_id": "uuid",
  "language": "en",
  "include_assumptions": true
}
```

### Salida

Estructura de propuesta con cabecera, comprador, productos, precios, supuestos, próximos pasos y advertencias. La salida podrá renderizarse como HTML; PDF es P1.

---

## `draft_email` — P0

### Entrada

```json
{
  "opportunity_id": "uuid",
  "proposal_id": "uuid",
  "language": "en",
  "tone": "professional_concise"
}
```

### Salida

Asunto, cuerpo, preguntas de clarificación y estado `needs_review`.

---

## `translate_message` — P1

No se utilizará en el camino feliz porque Qwen puede generar directamente en el idioma objetivo. Se conserva como capacidad futura cuando sea necesario preservar una traducción independiente.
