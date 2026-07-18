# Sprint 2 Bloque 7 — Acciones internas

- **Estado:** Ready for implementation
- **Sprint:** 2 — Núcleo funcional
- **Bloque:** 7
- **Baseline:** `69ec1ee`
- **Rama documental:** `docs/sprint2-block7-plan`
- **Rama de implementación prevista:** `feat/sprint2-internal-actions`
- **Fecha:** 2026-07-18
- **ADR vinculante:** ADR-013
- **Backlog:** AF-045, AF-046, AF-047

## Objetivo

Extender el camino feliz del backend desde una cotización y dos artefactos
válidos hasta un conjunto atómico, persistente e idempotente de acciones
internas:

1. resolver o crear el comprador mínimo;
2. crear la oportunidad CRM simulada;
3. crear el seguimiento estándar a siete días;
4. guardar memoria comercial explícita;
5. conservar trazabilidad completa;
6. terminar en revisión humana.

## Alcance incluido

- ADR-013 aceptado;
- migración reversible para `follow_up_tasks` e
  `internal_action_receipts`;
- modelos SQLAlchemy, enums y restricciones asociados;
- schemas Pydantic estrictos para las tres acciones;
- resolución o creación mínima de customer;
- servicio determinista de calificación de oportunidad;
- construcción determinista de seguimiento;
- extracción determinista y limitada de memorias;
- repositorios y servicio transaccional de acciones internas;
- claves y fingerprints de idempotencia;
- extensión acotada del orquestador;
- tool executions y eventos funcionales;
- resultados parciales y errores seguros;
- tests unitarios, de integración, migración y orquestación;
- documentación y evidencia de cierre.

## Fuera de alcance

- API HTTP;
- background tasks;
- endpoint de retry;
- frontend;
- aprobación o edición de artefactos;
- envío real de correo;
- CRM externo;
- calendario externo;
- notificaciones;
- reserva o modificación de stock;
- actualización de precios o cotizaciones;
- PDF o HTML final;
- autenticación;
- matching o fusión automática de compradores;
- múltiples seguimientos automáticos;
- invalidación o edición de memoria;
- nuevas llamadas a Qwen;
- nuevas tools seleccionables por el modelo;
- ejecución asíncrona o cola durable.

## Precondición

El Bloque 7 solo continúa cuando el run contiene referencias válidas a:

- recomendación validada;
- una cotización `draft` en EUR;
- una propuesta `needs_review`;
- un borrador de correo `needs_review`.

Las entidades deben pertenecer al mismo run y quote. Un run con cotización o
artefactos parciales conserva el resultado del Bloque 6 y no ejecuta acciones.

No se implementará backfill de runs históricos ni continuación automática de
runs que ya terminaron antes del Bloque 7. Los nuevos runs recorrerán el flujo
extendido.

## Decisiones de diseño

### 1. Capacidades internas

Se implementan contratos tipados para:

```text
create_crm_opportunity
create_followup_task
save_customer_memory
```

El orquestador las invoca en ese orden. No se registran en la allowlist de tools
que Qwen puede seleccionar.

Cada intento:

- crea una entrada `tool_execution`;
- valida entrada antes de escribir;
- devuelve un envelope tipado;
- registra referencias, conteos, duración y error seguro;
- no registra cadena de pensamiento ni información sensible.

### 2. Resolución del customer

Entrada lógica:

```json
{
  "agent_run_id": "uuid"
}
```

Reglas:

1. recuperar el run y la inquiry;
2. reutilizar un `customer_id` válido ya asociado;
3. en su ausencia, validar `company_name` y `market` desde
   `inquiry.extracted_data`;
4. crear el customer con país, contacto, email e idioma disponibles;
5. usar `en` como fallback de idioma;
6. asociar el customer a la inquiry dentro de la transacción;
7. rechazar identidad insuficiente sin crear placeholders.

No se busca otro customer por coincidencia de nombre o email.

### 3. Oportunidad determinista

Entrada persistible:

```json
{
  "inquiry_id": "uuid",
  "customer_id": "uuid",
  "title": "Rhein Selection GmbH — DE — 600 bottles",
  "stage": "proposal_draft",
  "priority": "high",
  "score": 90,
  "market": "DE",
  "channel": "specialty_retail",
  "estimated_bottles": 600,
  "target_date": "2026-09-16",
  "summary": "Qualified B2B opportunity with a validated product recommendation.",
  "idempotency_key": "run-uuid:create_crm_opportunity"
}
```

Fuentes autoritativas:

- inquiry y análisis validado;
- customer resuelto;
- recomendación validada;
- existencia de quote y artefactos;
- reglas de ADR-013.

Reglas:

- una oportunidad por inquiry;
- `stage=proposal_draft`;
- score 0-100 según ADR-013;
- prioridad derivada del score;
- `target_date` usa la fecha explícita o se calcula desde
  `received_at + target_horizon_days`;
- título y resumen usan plantillas, no Qwen;
- no se incluye subtotal, impuestos, transporte ni promesas de stock;
- una oportunidad histórica se reutiliza solo cuando pertenece a la misma
  inquiry y el receipt demuestra la misma operación;
- una colisión sin receipt equivalente es un conflicto seguro.

### 4. Seguimiento determinista

Entrada persistible:

```json
{
  "opportunity_id": "uuid",
  "title": "Follow up on proposal, pricing and samples",
  "due_at": "2026-07-25T15:00:00Z",
  "status": "pending",
  "idempotency_key": "run-uuid:create_followup_task"
}
```

Reglas:

- reloj UTC inyectable;
- vencimiento a siete días naturales;
- una tarea creada por la clave canónica del run;
- no se crea evento de calendario ni notificación;
- el título menciona muestras solo cuando fueron solicitadas.

### 5. Memoria explícita

Entrada lógica:

```json
{
  "customer_id": "uuid",
  "source_inquiry_id": "uuid",
  "memories": [
    {
      "category": "preference",
      "content": "Interested in Albariño for specialised retail in Germany.",
      "confidence": 1.0
    }
  ],
  "idempotency_key": "run-uuid:save_customer_memory"
}
```

Reglas:

- máximo 20 hechos;
- contenido 1-500 caracteres después de normalizar;
- categorías permitidas: `preference`, `requirement`, `interaction`;
- hechos derivados solo de campos explícitos validados;
- deduplicación por customer, categoría, contenido normalizado e inquiry;
- no se guarda dirección, contacto, identificador fiscal, presupuesto ni texto
  narrativo generado;
- repetir la operación devuelve los IDs existentes.

### 6. Idempotencia

Cada acción utiliza un `internal_action_receipt`.

Restricciones:

```text
unique(idempotency_key)
unique(agent_run_id, action_name)
```

El fingerprint usa JSON canónico validado:

- claves ordenadas;
- UUID, fecha y datetime serializados en formato canónico;
- enums representados por su valor;
- listas de memoria normalizadas y ordenadas de forma estable;
- hash SHA-256 hexadecimal.

El receipt guarda solo referencias resumidas. No duplica el contenido completo
de oportunidad, seguimiento o memoria.

### 7. Transacción

Patrón:

```text
persist step=persisting_actions and start events
commit
build and validate all deterministic inputs
begin transaction
resolve or create customer
create or reuse opportunity
create or reuse follow-up
create or reuse memories
persist receipts, tool results and success events
update result_payload and run terminal state
commit
```

No se mantiene una transacción abierta durante llamadas de red. Bloque 7 no
realiza llamadas de red.

### 8. Orquestación

Camino feliz extendido:

```text
generating_artifacts
  -> persisting_actions
  -> needs_review
```

`AgentRunStep` añade `persisting_actions`.

El run conserva `status=running` durante la fase. Al completar las tres acciones
termina `status=needs_review`, porque los artefactos siguen pendientes de
revisión humana.

### 9. Eventos mínimos

- `internal_actions_started`;
- `customer_resolution_started`;
- `customer_reused`;
- `customer_created`;
- `crm_opportunity_started`;
- `crm_opportunity_persisted`;
- `followup_task_started`;
- `followup_task_persisted`;
- `customer_memory_started`;
- `customer_memory_persisted`;
- `internal_action_reused`;
- `internal_action_rejected`;
- `internal_actions_rolled_back`;
- `internal_actions_completed`;
- `run_needs_review`.

Los eventos incluyen identificadores, action name, clave segura o fingerprint
abreviado, conteos, estado y errores seguros. No incluyen datos personales
innecesarios ni cadena de pensamiento.

### 10. Resultado del run

`agent_runs.result_payload` conserva recomendación, quote y artefactos, y añade:

```json
{
  "customer": {
    "customer_id": "uuid",
    "created": false
  },
  "opportunity": {
    "opportunity_id": "uuid",
    "stage": "proposal_draft",
    "priority": "high",
    "score": 90
  },
  "followup": {
    "followup_task_id": "uuid",
    "due_at": "2026-07-25T15:00:00Z",
    "status": "pending"
  },
  "memory": {
    "saved_count": 3,
    "memory_ids": ["uuid-1", "uuid-2", "uuid-3"]
  }
}
```

El payload no contiene email, dirección, identificador fiscal, contenido
completo de memorias ni entidades completas.

## Validación determinista

### Precondición comercial

- run existente y no terminal antes de entrar en la fase;
- inquiry existente;
- recomendación validada;
- quote perteneciente al run;
- dos artefactos del mismo run y quote;
- propuesta y correo en `needs_review`.

### Customer

- UUID válido cuando ya existe;
- customer existente si está asociado;
- company name no vacío y máximo 160;
- market ISO alpha-2;
- idioma ISO alpha-2;
- email máximo 320 cuando exista;
- no hay matching implícito.

### Oportunidad

- inquiry y customer coincidentes;
- título y resumen no vacíos;
- etapa conocida;
- score 0-100;
- prioridad consistente con score;
- market coincidente con el análisis;
- volumen y fecha coincidentes con datos validados;
- una oportunidad por inquiry.

### Seguimiento

- opportunity existente;
- `due_at` UTC;
- exactamente siete días desde el reloj inyectado;
- título no vacío;
- estado inicial `pending`.

### Memoria

- customer e inquiry coincidentes;
- categorías permitidas;
- contenido normalizado no vacío;
- máximo 20 hechos;
- sin campos sensibles prohibidos;
- sin duplicados dentro del lote ni contra memoria activa existente.

### Idempotencia

- clave canónica no vacía;
- action name conocida;
- fingerprint SHA-256 válido;
- misma clave y mismo contenido reutiliza;
- misma clave y contenido distinto rechaza;
- receipt y resultado coherentes.

## Manejo de errores

| Condición | Resultado |
|---|---|
| quote o artefacto ausente | conservar resultado parcial, `needs_review` |
| customer existente inválido | `needs_review`, sin escrituras |
| identidad insuficiente para customer nuevo | `needs_review`, sin escrituras |
| oportunidad previa sin receipt equivalente | `needs_review`, conflicto seguro |
| clave repetida con mismo fingerprint | reutilizar resultado |
| clave repetida con fingerprint distinto | `needs_review`, `IDEMPOTENCY_CONFLICT` |
| memoria sin hechos permitidos | completar con `saved_count=0` y warning |
| error de validación antes de transacción | `needs_review`, sin escrituras |
| error de persistencia | rollback completo de acciones; conservar Bloque 6 |
| imposibilidad de registrar estado de fallo | propagar error de infraestructura |

## Tests requeridos

### Migración

- upgrade crea `follow_up_tasks` e `internal_action_receipts`;
- FKs, checks, índices y restricciones únicas;
- downgrade reversible;
- SQLite foreign keys activas;
- upgrade desde head `0003`.

### Calificación

- score para cada intención;
- suma y límite 100;
- thresholds de prioridad;
- stage fija;
- título y resumen deterministas;
- target date explícita y derivada del horizonte.

### Customer

- reutilización de customer asociado;
- creación mínima para comprador desconocido;
- fallback de idioma;
- asociación a inquiry;
- rechazo por identidad insuficiente;
- ausencia de matching por nombre o email.

### Oportunidad

- creación válida;
- campos derivados correctos;
- una por inquiry;
- misma clave reutiliza;
- conflicto de contenido;
- rechazo de datos inconsistentes.

### Seguimiento

- vencimiento exacto a siete días;
- UTC y reloj inyectado;
- título con y sin muestras;
- persistencia e idempotencia.

### Memoria

- mapeo de campos permitidos;
- exclusión de datos sensibles;
- normalización y deduplicación;
- lote vacío válido con warning;
- máximo de hechos;
- idempotencia de lote;
- recuperación en una segunda sesión.

### Transacción y orquestación

- camino feliz termina `needs_review`;
- fase `persisting_actions` visible;
- no hay nueva llamada a Qwen;
- las tres acciones se registran en orden;
- rollback de las tres acciones ante fallo intermedio;
- eventos en orden y sin PII innecesaria;
- resultado final contiene solo referencias resumidas;
- resultado parcial de Bloque 6 no ejecuta acciones;
- reintento completo no duplica entidades;
- tool executions conservan intentos reutilizados y rechazados.

## Criterios de aceptación

1. Una quote y dos artefactos válidos producen una oportunidad persistida.
2. La oportunidad utiliza score y prioridad deterministas.
3. Se crea un seguimiento exactamente siete días después.
4. Se guardan solo memorias explícitas permitidas.
5. Un comprador desconocido identificable obtiene un perfil mínimo.
6. No se crea un customer cuando faltan empresa o mercado.
7. Repetir una acción con la misma clave y contenido no duplica datos.
8. Reutilizar una clave con otro contenido no sobrescribe datos.
9. Oportunidad, seguimiento, memorias y receipts se confirman atómicamente.
10. Una segunda sesión recupera la memoria guardada.
11. Las tres acciones aparecen en tool executions y eventos.
12. El run termina `needs_review`, no aprueba ni envía artefactos.
13. No se llama a Qwen durante las acciones.
14. No se modifica inventario.
15. La migración es reversible.
16. Ruff, mypy strict y pytest pasan.

## Definition of Done

- ADR-013 aceptado;
- documentación arquitectónica alineada;
- cierre documental del Bloque 6 corregido;
- migración reversible desde `0003`;
- modelos, repositorios y schemas tipados;
- calificación de oportunidad determinista;
- customer mínimo con validación estricta;
- seguimiento con reloj UTC inyectable;
- memoria explícita, limitada y deduplicada;
- receipts y fingerprints de idempotencia;
- unidad transaccional de acciones internas;
- orquestador extendido sin nuevas llamadas al modelo;
- tool executions, eventos y errores seguros;
- tests unitarios, integración y migración;
- README, changelog y verification actualizados al cierre;
- `make check-api` en verde;
- sin API, background task, frontend o integración externa.

## Orden de implementación

1. migración, enums y receipts;
2. modelos y repositorios;
3. schemas de acciones;
4. resolución del customer;
5. calificación y construcción de oportunidad;
6. seguimiento y memoria;
7. servicio transaccional e idempotencia;
8. extensión del orquestador;
9. eventos y errores seguros;
10. tests;
11. documentación de cierre.
