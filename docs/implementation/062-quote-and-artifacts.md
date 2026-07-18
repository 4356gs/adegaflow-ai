# Sprint 2 Bloque 6 — Cotización y artefactos

- **Estado:** Implemented and merged
- **Sprint:** 2 — Núcleo funcional
- **Bloque:** 6
- **Baseline:** `50316b0`
- **Rama documental:** `docs/sprint2-block6-plan`
- **Rama de implementación prevista:** `feat/sprint2-quote-artifacts`
- **Fecha:** 2026-07-13
- **ADR vinculante:** ADR-012
- **Rama de implementación:** `feat/sprint2-quote-artifacts`
- **PR:** #6
- **Merge commit:** `69ec1ee`
- **Verificación:** Ruff passed; mypy strict passed in 44 source files; 85 tests passed; 92% total coverage

## Objetivo

Extender el camino feliz del backend desde una recomendación validada hasta:

1. una cotización determinista persistida;
2. una propuesta comercial estructurada;
3. un borrador de correo estructurado;
4. un punto de control humano con estado `needs_review`.

## Alcance incluido

- migración reversible para `quotes`, `quote_items` y `generated_artifacts`;
- modelos SQLAlchemy y enums asociados;
- repositorios con restricciones de idempotencia por run;
- servicio determinista `calculate_quote`;
- prompt versionado `proposal_writer.v1`;
- prompt versionado `email_writer.v1`;
- schemas Pydantic estrictos para narrativa;
- ensamblado backend de datos comerciales verificados;
- extensión acotada del orquestador;
- eventos funcionales y errores seguros;
- tests unitarios, integración y migración;
- documentación y evidencia de verificación.

## Fuera de alcance

- creación o actualización de oportunidades CRM;
- seguimiento;
- escritura de memoria;
- envío real de correo;
- PDF;
- HTML final;
- firma o aceptación comercial;
- impuestos;
- transporte;
- seguros;
- aranceles;
- descuentos;
- margen comercial;
- conversión de moneda;
- reserva de inventario;
- API HTTP;
- ejecución asíncrona;
- frontend.

## Precondición

El Bloque 6 solo continúa cuando `agent_runs.result_payload` contiene una recomendación validada del esquema vigente.

No se implementará backfill ni reanudación de runs históricos completados antes del Bloque 6. Los nuevos runs recorrerán el flujo extendido.

## Decisiones de diseño

### 1. Propiedad

De acuerdo con ADR-012:

- la cotización pertenece al `agent_run`;
- la inquiry se deriva mediante `agent_run.inquiry_id`;
- la oportunidad futura se deriva por la inquiry compartida y no se materializa en la cotización;
- los artefactos pertenecen al run y a la cotización;
- no existe un agregado adicional.

### 2. Cotización como servicio determinista

`calculate_quote` no es una tool seleccionable por Qwen. El orquestador la invoca después de validar la recomendación.

Entrada lógica:

```json
{
  "agent_run_id": "uuid"
}
```

El servicio recupera exclusivamente:

- recomendación validada;
- `product_id`;
- SKU y nombre oficial;
- `quantity_bottles`;
- `unit_price_cents`;
- `units_per_case`;
- moneda;
- presupuesto EUR conocido, cuando exista.

Fórmulas:

```text
line_total_cents = quantity_bottles * unit_price_cents
subtotal_cents = sum(line_total_cents)
cases = quantity_bottles // units_per_case
```

Reglas:

- todos los importes son `int` en céntimos;
- la única moneda admitida en el MVP es EUR;
- no se aceptan precios proporcionados por Qwen;
- no se redondean importes con `float`;
- no se modifican cantidades silenciosamente;
- cada cantidad debe seguir siendo divisible por `units_per_case`, como exige el Bloque 5;
- no se consulta ni reserva stock durante el cálculo;
- un presupuesto excedido genera una advertencia, no una corrección automática;
- subtotal y totales de línea deben ser reproducibles.

Supuestos persistidos:

- precio unitario snapshot de la recomendación validada;
- impuestos no incluidos;
- transporte no incluido;
- seguros no incluidos;
- aranceles y aduanas no incluidos;
- stock no reservado;
- cotización borrador sujeta a revisión humana.

### 3. Persistencia

#### `quotes`

Campos mínimos:

- `id`;
- `agent_run_id`, FK obligatorio y único;
- `currency`, limitado a EUR;
- `subtotal_cents`;
- `status`, inicialmente `draft`;
- `assumptions`, JSON versionado;
- `created_at`.

#### `quote_items`

Campos mínimos:

- `id`;
- `quote_id`;
- `product_id`;
- `quantity_bottles`;
- `unit_price_cents`;
- `line_total_cents`;
- `cases`.

Restricción:

```text
unique(quote_id, product_id)
```

#### `generated_artifacts`

Campos mínimos:

- `id`;
- `agent_run_id`, FK obligatorio;
- `quote_id`, FK obligatorio;
- `artifact_type`, `proposal` o `email_draft`;
- `language`, ISO 639-1;
- `schema_version`;
- `content`, JSON;
- `review_status`, inicialmente `needs_review`;
- `created_at`.

Restricción:

```text
unique(agent_run_id, artifact_type)
```

### 4. Propuesta comercial

Prompt:

```text
proposal_writer.v1
```

Qwen recibe solo contexto necesario:

- idioma objetivo;
- comprador conocido;
- mercado y canal;
- resumen y rationale de la recomendación;
- nombres oficiales de productos;
- campos faltantes;
- supuestos y exclusiones;
- próximos pasos permitidos.

Qwen devuelve únicamente narrativa:

- `schema_version`;
- `headline`;
- `executive_summary`;
- `product_positioning` por `product_id`;
- `next_steps`;
- `open_questions`;
- `warnings`.

Qwen no devuelve campos autoritativos de:

- precio;
- subtotal;
- moneda;
- cantidad;
- cajas;
- stock;
- condiciones legales.

El backend ensambla el artefacto final combinando la narrativa validada con:

- comprador;
- líneas de cotización;
- subtotal;
- moneda;
- supuestos;
- exclusiones;
- estado de revisión.

### 5. Borrador de correo

Prompt:

```text
email_writer.v1
```

El idioma se resuelve de forma determinista:

1. idioma detectado válido de la inquiry;
2. idioma preferido conocido del cliente;
3. fallback `en`.

Qwen devuelve:

- `schema_version`;
- `subject`;
- `introduction`;
- `recommendation_summary`;
- `next_step`;
- `questions`;
- `closing`;
- `warnings`.

El backend añade un bloque comercial determinista derivado de la cotización.

Qwen no afirma que:

- el correo fue enviado;
- la propuesta fue aprobada;
- el stock fue reservado;
- los importes incluyen conceptos excluidos.

### 6. Presupuesto de llamadas al modelo

El presupuesto de selección del Bloque 5 no cambia.

La redacción utiliza límites independientes:

```text
MAX_PROPOSAL_ATTEMPTS = 2
MAX_EMAIL_ATTEMPTS = 2
```

Cada límite representa un intento inicial y una reparación controlada.

No existen tool calls durante la redacción de artefactos.

### 7. Orquestación

Camino feliz extendido:

```text
validating_recommendation
  -> calculating_quote
  -> generating_artifacts
  -> needs_review
```

El run exitoso del Bloque 6 termina `needs_review`, no `completed`, porque los artefactos requieren revisión humana.

Patrón transaccional:

```text
persist step/event
commit
perform deterministic calculation or provider call
validate
persist entity/event
commit
```

Nunca se mantiene una transacción SQLite abierta durante una llamada a Qwen.

### 8. Eventos mínimos

- `quote_calculation_started`;
- `quote_calculated`;
- `quote_persisted`;
- `proposal_generation_started`;
- `proposal_received`;
- `proposal_rejected`;
- `proposal_persisted`;
- `email_generation_started`;
- `email_draft_received`;
- `email_draft_rejected`;
- `email_draft_persisted`;
- `artifact_generation_partial`;
- `run_needs_review`.

Los eventos contienen identificadores, versiones, conteos, estados, warnings y errores seguros. No contienen cadena de pensamiento.

### 9. Resultado del run

`agent_runs.result_payload` conserva la recomendación validada y añade referencias resumidas:

```json
{
  "recommendation": {},
  "quote": {
    "quote_id": "uuid",
    "currency": "EUR",
    "subtotal_cents": 420000,
    "status": "draft"
  },
  "artifacts": [
    {
      "artifact_id": "uuid",
      "artifact_type": "proposal",
      "review_status": "needs_review"
    },
    {
      "artifact_id": "uuid",
      "artifact_type": "email_draft",
      "review_status": "needs_review"
    }
  ]
}
```

El payload no duplica el contenido completo de cotización ni artefactos.

## Validación determinista

### Cotización

- run existente;
- recomendación validada;
- al menos una línea;
- IDs únicos;
- cantidades positivas;
- precios enteros no negativos;
- EUR;
- multiplicación exacta;
- subtotal igual a la suma de líneas;
- datos snapshot coincidentes con la recomendación.

### Propuesta

- schema version conocida;
- idioma válido;
- `product_id` limitado a productos cotizados;
- una narrativa como máximo por producto;
- secciones obligatorias no vacías;
- sin campos comerciales autoritativos generados por el modelo.

### Correo

- schema version conocida;
- asunto y cuerpo no vacíos;
- idioma coincidente;
- preguntas como lista;
- sin afirmación de envío, aprobación o reserva;
- referencia a artefactos existentes.

## Idempotencia

- un quote por run;
- una línea por producto dentro del quote;
- un artefacto por tipo y run;
- repetir una operación con el mismo contenido devuelve la entidad existente;
- un conflicto de contenido no sobrescribe silenciosamente y termina `needs_review`.

## Manejo de errores

| Condición | Resultado |
|---|---|
| recomendación ausente o inválida | `failed` |
| moneda distinta de EUR | `needs_review` |
| error aritmético o integridad imposible | `failed` |
| presupuesto excedido | quote válido con warning |
| Qwen falla antes de crear artefactos | quote persistido, `needs_review` |
| propuesta válida y correo falla | resultado parcial, `needs_review` |
| JSON inválido tras reparación | resultado parcial o `failed` si no existe utilidad |
| error de persistencia | rollback de la unidad actual y `failed` |
| duplicado idempotente | reutilizar entidad |
| conflicto idempotente | `needs_review` |

## Tests requeridos

### Migración

- upgrade crea las tres tablas;
- restricciones y FKs;
- downgrade reversible;
- SQLite foreign keys activas.

### Cotización

- una línea;
- varias líneas;
- cálculo exacto de cajas;
- rechazo de cantidades no divisibles;
- subtotal exacto;
- presupuesto excedido;
- moneda no admitida;
- rechazo de datos inconsistentes;
- idempotencia.

### Artefactos

- carga de prompts versionados;
- propuesta válida;
- propuesta inválida y reparación;
- email válido;
- email inválido y reparación;
- idioma fallback;
- persistencia;
- unicidad por tipo;
- resultado parcial.

### Orquestación

- camino feliz termina `needs_review`;
- quote persiste antes de llamar a Qwen;
- no hay transacción abierta durante provider calls;
- fallo de propuesta;
- fallo de correo;
- error de persistencia;
- eventos en orden;
- payload final solo contiene referencias resumidas.

## Criterios de aceptación

1. Una recomendación válida produce una cotización reproducible en EUR.
2. Ningún importe vinculante procede del modelo.
3. La cotización persiste antes de generar narrativa.
4. Propuesta y correo se validan con schemas versionados.
5. Ambos artefactos quedan `needs_review`.
6. Un fallo de narrativa no elimina la cotización.
7. No se crea una oportunidad.
8. No se envía correo.
9. No se reserva stock.
10. La trazabilidad permite explicar cada fase sin cadena de pensamiento.
11. La migración es reversible.
12. Ruff, mypy strict y pytest pasan.

## Definition of Done

- ADR-012 aceptado;
- documentación arquitectónica alineada;
- migración reversible;
- modelos y repositorios tipados;
- servicio de cotización determinista;
- prompts y schemas versionados;
- ensambladores de propuesta y correo;
- orquestador extendido;
- errores seguros y resultados parciales;
- tests unitarios e integración;
- README, changelog y verification actualizados al cierre;
- `make check-api` en verde;
- sin CRM, follow-up, API o frontend.

## Orden de implementación

1. migración y enums;
2. modelos y repositorios;
3. schemas de cotización;
4. servicio determinista;
5. prompts y schemas de narrativa;
6. persistencia de artefactos;
7. extensión del orquestador;
8. eventos y manejo de fallos parciales;
9. tests;
10. documentación de cierre.
