# Sprint 3 — Bloque 3: ejecución observable

## Estado

- **Estado:** Aprobada para implementación el 2026-08-05
- **Baseline de código y documentación:** `main@83eae18773dff1f65db23b8a8206f5e43cc9f6de`
- **Baseline funcional:** Sprint 3, Bloque 2 fusionado mediante PR #17
- **Verificación declarada del baseline:** `make check-web`, 43 pruebas frontend aprobadas
- **Rama de implementación prevista:** `feat/sprint3-run-observability`
- **Objetivo único:** convertir `/runs/[runId]` en un workspace que muestre el progreso real y ordenado de una ejecución, sus tools, su estado terminal y el retry permitido por el backend, sin incorporar todavía el resultado comercial del Bloque 4.

Este documento concreta exclusivamente el Bloque 3 definido en
`068-sprint-3-implementation-plan.md`. No autoriza código antes de su aprobación
ni modifica el contrato backend cerrado en Sprint 2 y ajustado en el Bloque 1.

## Fuentes de verdad y resolución de discrepancias

La implementación debe derivarse de:

1. `067-sprint-3-charter.md`;
2. `068-sprint-3-implementation-plan.md`;
3. `069-sprint-3-acceptance-and-definition-of-done.md`;
4. `031-frontend-experience.md`;
5. `026-api-contracts.md` y `029-observability-and-errors.md`;
6. los schemas Pydantic y endpoints vigentes en `apps/api`;
7. los tipos y el cliente same-origin de `apps/web/src/lib/api/`;
8. la implementación fusionada del Bloque 2.

Cuando un ejemplo narrativo antiguo difiera del schema efectivo, prevalecen el
schema Pydantic y los tipos frontend de `main@83eae18`. En particular,
`PublicEvent` no expone `summary`, `name` ni un `status` propio. La UI no debe
inventarlos como datos del backend: construirá labels de presentación a partir
de `event_type`, `step`, `tool_name` y `action_name`.

El README de ese commit no refleja todavía la fusión de los Bloques 1 y 2. Esa
deriva de estado no cambia el baseline de este documento y se corregirá en el
cierre documental correspondiente, no mediante cambios de producto en este
bloque.

## Resultado observable

Al terminar el bloque, una persona puede:

1. abrir un run real desde el cockpit o después de crear una consulta;
2. ver su estado global y paso actual con lenguaje comprensible;
3. observar cómo llegan eventos nuevos sin recargar la página;
4. recorrer una timeline completa, ordenada y sin duplicados;
5. identificar las cuatro tools públicas cuando el evento incluya `tool_name`;
6. distinguir acciones internas de tools invocadas por el modelo;
7. comprender `completed`, `needs_review` y `failed` como resultados distintos;
8. ver el error seguro y el correlation ID de un fallo;
9. reintentar únicamente un run fallido con `retryable=true`;
10. navegar al nuevo intento y regresar al intento original mediante
    `retry_of_run_id`.

El workspace no muestra análisis, recomendación, stock, cotización, propuesta,
correo, oportunidad, seguimiento ni memoria. Esas secciones pertenecen al
Bloque 4 y no se consultará su endpoint en este bloque.

## Alcance

### Funcional

- reemplazar el placeholder de `/runs/[runId]` por un workspace observable;
- validar el formato UUID antes de hacer requests;
- obtener el detalle mediante `api.getRun(runId)`;
- obtener eventos incrementales mediante `api.getEvents(runId, afterSequence, 100)`;
- mantener un cursor por run y una colección ordenada de eventos;
- agrupar eventos consecutivos por paso sin alterar su orden;
- traducir estados, pasos, tipos de evento, tools y acciones internas a labels;
- detener el polling de forma determinista al alcanzar un estado terminal y
  haber drenado sus eventos;
- pausar polling con la pestaña oculta y reanudarlo al volver a estar visible;
- conservar datos ya cargados ante un error posterior de lectura;
- permitir recuperación manual de lecturas fallidas;
- mostrar retry solo cuando el contrato efectivo lo autoriza;
- ejecutar retry con una clave idempotente estable y navegar al nuevo run;
- mostrar el vínculo del nuevo intento hacia el original;
- cubrir carga, progreso, terminales, errores, timeline vacía, retry y estados
  de contrato inconsistente;
- mantener accesibilidad y responsive desde 360 px.

### Técnica

- usar únicamente el cliente centralizado y el proxy same-origin existentes;
- no añadir librería global de estado, data fetching o polling;
- implementar timers cancelables y requests no solapados;
- abortar requests al desmontar o cambiar `runId`;
- modelar el acumulador de eventos como utilidad pura y probada;
- usar `sessionStorage` solo para la intención de retry pendiente;
- reutilizar los tipos `AgentRunDetail`, `EventList`, `PublicEvent` y
  `RunAccepted` ya existentes;
- no añadir dependencias runtime ni de pruebas salvo aprobación documental
  previa.

## Exclusiones

Queda explícitamente fuera de alcance:

- `GET /api/v1/agent-runs/{id}/result` y cualquier render de `RunResult`;
- mensaje original, análisis, faltantes, recomendación, productos, stock,
  quote, propuesta, email draft, customer, oportunidad, follow-up y memoria;
- edición, aprobación o rechazo persistente de artefactos;
- envío de correo, reserva de stock o sincronización externa;
- retry de `completed`, `needs_review` o `failed` con `retryable=false`;
- retry automático al cargar la página o recuperar conectividad;
- reiniciar o mutar el intento original;
- reverse lookup desde un run original hacia todos sus retries;
- filtros, búsqueda, métricas o navegación adicional del cockpit;
- WebSockets, SSE, long polling o streaming de tokens;
- estado global, React Query, SWR o dependencias equivalentes;
- nuevos endpoints, schemas, migraciones, modelos, repositorios o servicios;
- cambios en Qwen, prompts, tools, reglas comerciales u orquestación;
- exponer argumentos, outputs completos, prompts, tokens, razonamiento, secretos
  o stack traces;
- E2E completo y resultado comercial, reservados para Bloques 4 y 5;
- autenticación, roles, multitenencia, PostgreSQL, cola durable o múltiples
  workers.

## Contrato UI de `/runs/[runId]`

### Composición

La ruta mantiene la navegación del shell y presenta tres zonas:

1. **Cabecera del run**
   - enlace “Volver al cockpit”;
   - estado global con texto e icono;
   - paso actual con label legible;
   - inicio y finalización, si existe, en fecha/hora local;
   - identificador del run;
   - correlation ID en detalles de soporte;
   - si `retry_of_run_id` existe, enlace “Reintento de {id abreviado}” al run
     original.
2. **Estado y recuperación**
   - mensaje específico para `queued`, `running`, `completed`, `needs_review` o
     `failed`;
   - error seguro del run cuando exista;
   - estado de sincronización o lectura degradada;
   - retry únicamente bajo la regla vinculante definida más adelante.
3. **Timeline**
   - grupos consecutivos por `step`;
   - eventos en secuencia ascendente;
   - hora local, label y categoría textual por evento;
   - tool o acción interna cuando el payload público lo permita;
   - detalles técnicos acotados: `event_type`, `sequence` y `error_code` seguro.

No se renderiza JSON crudo. Los IDs pueden abreviarse visualmente, pero el
enlace y el nombre accesible conservan el ID completo.

### Jerarquía visual

- el estado global y el paso actual dominan la cabecera;
- la timeline es el contenido principal del bloque;
- los detalles técnicos se presentan en disclosure secundario;
- el retry nunca compite visualmente con el estado ni parece una acción normal
  para un resultado correcto;
- `needs_review` utiliza lenguaje de revisión humana, no de error;
- `completed` no promete que un correo fue enviado ni que una propuesta fue
  aprobada.

## Contrato API efectivo

El navegador llama exclusivamente a las rutas same-origin ya encapsuladas en
`api`.

| Operación | Método efectivo | Uso en Bloque 3 |
|---|---|---|
| Detalle del run | `GET /api/v1/agent-runs/{runId}` | Estado, paso, error seguro, retryable, relación entre intentos, correlation ID y última secuencia |
| Eventos incrementales | `GET /api/v1/agent-runs/{runId}/events?after_sequence={cursor}&limit=100` | Timeline incremental y señal terminal |
| Retry autorizado | `POST /api/v1/agent-runs/{runId}/retry` con `Idempotency-Key` | Crear un intento nuevo e inmutable enlazado al original |

No se usa `result_url` ni `api.getResult` en este bloque.

### `AgentRunDetail` consumido

La UI puede usar únicamente:

- `id`, `inquiry_id`, `retry_of_run_id` y `correlation_id`;
- `status` y `current_step`;
- `started_at` y `completed_at`;
- `error.code` y `error.message` cuando existan;
- `retryable` calculado por el backend;
- `last_event_sequence`;
- `events_url` y `result_url` pueden validarse o ignorarse, pero no se usan para
  saltarse el cliente tipado.

`model`, `prompt_versions` y `references` permanecen fuera de la presentación
P0 de este bloque.

### `EventList` y `PublicEvent` consumidos

`EventList` contiene:

- `agent_run_id`;
- `events`;
- `last_sequence`;
- `terminal`.

Cada evento contiene únicamente:

- `sequence`;
- `event_type`;
- `step`;
- `payload` público;
- `created_at`.

La allowlist pública vigente del payload es:

```text
error_code, reason, schema_version, missing_field_count, model_round,
tool_call_count, validation_status, quote_id, artifact_id, artifact_type,
opportunity_id, followup_task_id, memory_id, action_name, tool_name
```

La UI no presupone que todos esos campos estén presentes ni accede a cualquier
otro campo que pudiera aparecer por error. `tool_name` solo se muestra si es un
string reconocido o como “Tool no reconocida” con su código técnico visible.

### Errores HTTP

- `ApiError.message`, `ApiError.code` y `ApiError.correlationId` son la única
  fuente para errores de request;
- `404 AGENT_RUN_NOT_FOUND` produce un estado no encontrado, no polling;
- `409 RUN_NOT_RETRYABLE` elimina la acción de retry tras refrescar el detalle;
- `409 IDEMPOTENCY_CONFLICT` es definitivo para esa intención y nunca rota la
  clave automáticamente;
- errores de transporte o contenido inesperado conservan el último snapshot y
  permiten reintentar la lectura o el mismo comando idempotente;
- nunca se muestran `details` completos, cuerpo crudo, stack trace ni URL
  interna.

## Modelo de estados

### Estados del run

| Valor | Label | Tratamiento |
|---|---|---|
| `queued` | En cola | Progreso activo; polling habilitado |
| `running` | Procesando | Progreso activo; muestra paso y timeline |
| `needs_review` | Listo para revisión | Terminal esperado; sin retry |
| `completed` | Completado | Terminal correcto; sin retry |
| `failed` | No se pudo completar | Terminal; muestra error y retry solo si `retryable=true` |

Estados terminales vinculantes: `completed`, `needs_review` y `failed`.

### Labels de pasos

| `current_step` / `step` | Label |
|---|---|
| `queued` | En cola |
| `analyzing` | Analizando consulta |
| `retrieving_memory` | Recuperando historial |
| `selecting_products` | Seleccionando productos |
| `checking_stock` | Verificando stock |
| `validating_recommendation` | Validando recomendación |
| `calculating_quote` | Calculando cotización |
| `generating_artifacts` | Preparando borradores |
| `persisting_actions` | Registrando acciones comerciales |
| `completed` | Ejecución completada |
| `needs_review` | Pendiente de revisión humana |
| `failed` | Ejecución fallida |

Un valor futuro desconocido se presenta como “Paso no reconocido” y conserva
el código en detalles. No rompe el workspace ni se convierte en un estado
terminal por inferencia del frontend.

### Labels de tools

| `tool_name` | Label |
|---|---|
| `search_catalog` | Buscar catálogo |
| `get_product_details` | Consultar producto |
| `check_stock` | Verificar stock |
| `retrieve_customer_history` | Recuperar historial |

### Labels de acciones internas

| `action_name` | Label |
|---|---|
| `create_crm_opportunity` | Registrar oportunidad demo |
| `create_followup_task` | Programar seguimiento demo |
| `save_customer_memory` | Guardar memoria del cliente |

Estas acciones se identifican como “Acción interna”, nunca como tool solicitada
por Qwen ni como integración externa.

### Familias de eventos

El mapper usa una tabla cerrada para los eventos conocidos. Como mínimo cubre:

| Familia | Eventos | Categoría visible |
|---|---|---|
| Run | `run_created`, `run_completed`, `run_needs_review`, `run_failed`, `run_interrupted`, `dispatch_failed` | Registrado, completado, revisión o fallo |
| Análisis | `analysis_started`, `analysis_reused`, `analysis_completed` | En curso, reutilizado o completado |
| Memoria | `memory_retrieval_started`, `memory_retrieval_skipped` | En curso u omitido |
| Selección | `selection_round_started`, `selection_round_completed` | En curso o completado |
| Tools | `tool_requested`, `tool_started`, `tool_succeeded`, `tool_failed`, `tool_rejected`, `tool_retry_scheduled` | Solicitada, en curso, completada, fallida, rechazada o reprogramada |
| Recomendación | `recommendation_draft_requested`, `recommendation_draft_received`, `recommendation_correction_requested`, `recommendation_correction_received`, `recommendation_validation_started`, `recommendation_validated`, `recommendation_rejected` | En curso, recibida, validada o rechazada |
| Cotización | `quote_calculation_started`, `quote_calculated`, `quote_persisted` | En curso o completada |
| Borradores | `proposal_generation_started`, `proposal_received`, `proposal_rejected`, `proposal_persisted`, `email_generation_started`, `email_draft_received`, `email_draft_rejected`, `email_draft_persisted`, `artifact_generation_partial` | En curso, preparada, rechazada o parcial |
| Acciones internas | `internal_actions_started`, `customer_resolution_started`, `customer_reused`, `customer_created`, `crm_opportunity_started`, `crm_opportunity_persisted`, `followup_task_started`, `followup_task_persisted`, `customer_memory_started`, `customer_memory_persisted`, `internal_action_reused`, `internal_action_rejected`, `internal_actions_rolled_back`, `internal_actions_completed` | En curso, completada, reutilizada, rechazada o revertida |

Un `event_type` desconocido permanece en la secuencia con label “Actividad
registrada” y su código técnico. No se descarta ni se le atribuye éxito o fallo.

## Polling incremental

### Estado local por workspace

```text
runDetail | null
eventsBySequence
orderedSequences
lastSequence
readState
inFlight
visibility
```

No se persisten eventos ni detalle en almacenamiento del navegador. Al volver a
abrir la ruta se reconstruyen desde el backend, fuente autoritativa.

### Algoritmo vinculante

1. validar `runId`; si no es UUID válido, mostrar error local y no llamar la API;
2. iniciar una única operación de hidratación;
3. obtener `AgentRunDetail`;
4. solicitar eventos con `after_sequence=0` y `limit=100`;
5. aplicar cada página al acumulador y avanzar solo hasta la última secuencia
   válida y contigua;
6. mientras el cursor sea menor que `runDetail.last_event_sequence`, solicitar
   la página siguiente de forma secuencial;
7. si el detalle es terminal, detenerse solo después de alcanzar su
   `last_event_sequence`;
8. si `EventList.terminal=true` pero el detalle leído aún no era terminal,
   refrescar inmediatamente el detalle, drenar cualquier evento restante y
   volver a evaluar;
9. si el run continúa activo, programar el siguiente ciclo 1.5 segundos después
   de terminar el ciclo actual;
10. nunca usar `setInterval`; nunca iniciar una lectura mientras otra del mismo
    workspace esté activa;
11. al ocultarse la pestaña, cancelar el timer futuro sin perder el cursor;
12. al volver a `visible`, ejecutar un ciclo inmediato;
13. al desmontar o cambiar `runId`, cancelar timer y requests pendientes;
14. al producirse error de lectura, detener el ciclo automático, conservar los
    datos válidos y ofrecer “Volver a intentar actualización”.

El botón de recuperación repite únicamente GETs desde el último cursor
confirmado. Nunca crea un run ni rota una clave.

### Integridad del acumulador

- la primera secuencia esperada es `lastSequence + 1`;
- eventos repetidos idénticos por `sequence` se ignoran;
- una misma secuencia con contenido distinto es error de contrato;
- un salto de secuencia es error de contrato y no mueve el cursor más allá del
  hueco;
- `agent_run_id` debe coincidir con la ruta;
- `EventList.last_sequence` debe coincidir con el último evento retornado o con
  `after_sequence` si la página está vacía;
- una página vacía cuando el detalle anuncia secuencias pendientes es error de
  sincronización y no genera un bucle inmediato;
- la UI conserva los eventos válidos y muestra un estado recuperable ante
  cualquier inconsistencia;
- los grupos de timeline son consecutivos: pasos separados en el tiempo no se
  reordenan ni fusionan globalmente.

## Estados visibles de la ruta

| Estado | Tratamiento |
|---|---|
| ID inválido | Mensaje local, sin request, enlace al cockpit |
| Carga inicial | Estado anunciable sin datos ficticios |
| No encontrado | Mensaje seguro, correlation ID si existe y enlace al cockpit |
| `queued` sin eventos adicionales | Cabecera activa y timeline con estado vacío explícito |
| `running` | Paso actual, eventos acumulados y actualización discreta |
| Lectura degradada | Conserva snapshot, explica interrupción y permite repetir GET |
| Contrato inconsistente | Conserva datos válidos, no avanza cursor y permite resincronizar |
| `completed` | Terminal correcto; sin retry ni resultado comercial en este bloque |
| `needs_review` | Terminal útil pendiente de revisión; no se presenta como fallo |
| `failed`, no retryable | Error seguro y correlation ID; sin botón de retry |
| `failed`, retryable | Error seguro, correlation ID y botón “Crear nuevo intento” |
| Retry en curso | Botón bloqueado, progreso anunciable y sin doble submit |
| Retry con transporte incierto | Misma clave disponible para “Continuar reintento” |
| Retry aceptado | Navegación con `replace` al nuevo run; ningún POST adicional |

## Retry auditable e idempotente

### Regla de disponibilidad

El control aparece si y solo si:

```text
runDetail.status === "failed" && runDetail.retryable === true
```

El frontend no calcula retryability desde `error.code`. `needs_review` nunca es
retryable aunque conserve resultados parciales.

### Flujo

```text
idle → submitting → accepted → navigating
              ↘ transport_error → resume_same_key
              ↘ definitive_error
```

1. adquirir una guardia síncrona antes de cualquier `await`;
2. generar una sola `retryKey` con `crypto.randomUUID()`;
3. persistir intención antes del POST;
4. llamar `api.retryRun(originalRunId, retryKey)`;
5. persistir `agent_run_id` aceptado;
6. navegar con `router.replace` a `/runs/{agent_run_id}`;
7. limpiar la intención cuando el workspace del nuevo run confirma el destino.

El registro versionado en `sessionStorage` contiene solamente:

```text
version, originalRunId, retryKey, stage, acceptedRunId?
```

Reglas:

- una recarga no reenvía automáticamente la mutación;
- si la respuesta es incierta, el usuario continúa explícitamente con la misma
  clave y el mismo run original;
- si ya existe `acceptedRunId`, continuar solo navega y no repite el POST;
- doble clic no produce más de un POST lógico;
- `IDEMPOTENCY_CONFLICT` nunca genera otra clave automáticamente;
- una nueva intención explícita solo puede comenzar después de descartar la
  anterior;
- un `RUN_NOT_RETRYABLE` obliga a refrescar el detalle y retirar el control;
- el nuevo workspace muestra el enlace al original mediante
  `retry_of_run_id`;
- el intento original permanece inmutable.

## Accesibilidad y responsive

- un único `h1` identifica la ejecución;
- regiones de estado usan `role="status"` o `aria-live="polite"` sin anunciar
  cada tick silencioso;
- cambios de estado global sí se anuncian una vez;
- timeline usa lista semántica y headings por grupo;
- cada evento comunica texto e icono, no solo color;
- disclosure técnico es operable por teclado;
- foco visible en enlaces, retry y recuperación;
- tras un error de retry, el foco llega al resumen de error;
- durante retry el control está deshabilitado y usa `aria-disabled`;
- no se mueve el foco por cada actualización de polling;
- timestamps usan elementos `time` con `dateTime` original;
- desde 360 px la cabecera, acciones y timeline se apilan sin scroll horizontal;
- IDs y códigos largos pueden partirse sin deformar el layout;
- `prefers-reduced-motion` sigue respetado;
- la timeline no usa animación como única indicación de progreso.

## Estrategia de pruebas

### Unitarias

- mapping de los cinco estados y doce pasos;
- mapping de las cuatro tools y tres acciones internas;
- eventos conocidos y fallback de evento desconocido;
- formato de fechas y IDs;
- acumulación ordenada;
- avance del cursor;
- deduplicación idéntica;
- detección de secuencia conflictiva, hueco, run ajeno y `last_sequence`
  inconsistente;
- agrupación consecutiva por paso;
- clasificación terminal basada en `status`, no en el event type;
- serialización, restauración y descarte de intención de retry;
- estabilidad y seguridad de `retryKey`.

### Componentes y ruta

- UUID inválido sin llamadas API;
- carga inicial;
- no encontrado y error inicial;
- cabecera para cada estado;
- timeline vacía, con eventos, tools, acciones y evento desconocido;
- estado degradado sin perder eventos cargados;
- `needs_review` diferenciado de `failed`;
- retry visible únicamente con `failed && retryable`;
- error seguro y correlation ID;
- enlace desde un retry hacia el original;
- ausencia total de análisis y resultado comercial;
- roles, labels, foco y estados no dependientes de color.

### Polling con reloj controlado

- hidratación obtiene detalle antes de decidir terminalidad;
- usa `after_sequence=0`, luego el último cursor confirmado;
- pagina secuencialmente cuando existen más de 100 eventos;
- no solapa requests aunque una respuesta tarde más de 1.5 segundos;
- no duplica eventos por replay;
- detecta transición activa → terminal y drena el último evento;
- no programa más ciclos después de terminal;
- pausa en `document.hidden` y reanuda inmediatamente en `visible`;
- aborta al desmontar o cambiar de run;
- error de lectura detiene el ciclo y la acción manual lo reanuda desde el mismo
  cursor.

### Retry

- genera una clave nueva por intención y la conserva en errores de transporte;
- doble clic produce un POST lógico;
- replay con la misma clave navega al mismo run aceptado;
- recarga con POST incierto no reenvía sin confirmación explícita;
- intención con `acceptedRunId` navega sin POST;
- `IDEMPOTENCY_CONFLICT` no rota la clave;
- `RUN_NOT_RETRYABLE` retira el control tras refrescar;
- `router.replace` apunta al run retornado;
- el run original no se muta desde la UI.

### Contrato y regresión

- `api.getRun`, `api.getEvents` y `api.retryRun` conservan paths, query y header
  actuales;
- el payload público no expone campos fuera de la allowlist;
- ningún request del bloque usa `api.getResult`;
- ningún request apunta directamente a FastAPI;
- las 43 pruebas del baseline continúan aprobadas;
- no se requiere Qwen live.

### Evidencia manual del bloque

- navegación completa por teclado;
- foco visible y error de retry enfocado;
- pausa y reanudación al cambiar visibilidad de pestaña;
- layout sin overflow a 360 px y en escritorio;
- comprensión visual de `needs_review` frente a `failed`;
- ausencia de botones que prometan funciones del Bloque 4.

### Gates

```bash
make check-web
git diff --check
```

Si se modifica accidentalmente backend, contrato compartido, dependencia,
Compose o CI, el cambio queda fuera de alcance hasta documentarse y aprobarse.

## Criterios de aceptación

| ID | Criterio verificable |
|---|---|
| B3-AC-01 | `/runs/[runId]` valida el UUID y no llama la API cuando es inválido. |
| B3-AC-02 | Un UUID válido carga `AgentRunDetail` mediante el cliente same-origin existente. |
| B3-AC-03 | La cabecera muestra estado, paso, timestamps disponibles, run ID y correlation ID con labels comprensibles. |
| B3-AC-04 | `queued`, `running`, `completed`, `needs_review` y `failed` tienen tratamientos textuales distintos y no dependen solo del color. |
| B3-AC-05 | `needs_review` se presenta como resultado útil pendiente de revisión, no como error ni como run retryable. |
| B3-AC-06 | El primer request de eventos usa `after_sequence=0&limit=100`. |
| B3-AC-07 | Los requests posteriores usan exclusivamente la última secuencia contigua confirmada. |
| B3-AC-08 | Eventos incrementales se acumulan en orden sin huecos ni duplicados. |
| B3-AC-09 | Páginas de 100 eventos se drenan secuencialmente sin requests solapados. |
| B3-AC-10 | Un hueco, conflicto de secuencia, run ajeno o cursor inconsistente detiene el avance y muestra recuperación segura. |
| B3-AC-11 | La timeline agrupa pasos consecutivos sin reordenar eventos. |
| B3-AC-12 | Los doce pasos conocidos tienen labels cerrados y un paso desconocido no rompe la ruta. |
| B3-AC-13 | Las cuatro tools públicas se identifican por `tool_name`; inputs y outputs no se muestran. |
| B3-AC-14 | Las tres acciones internas se distinguen de las tools y de integraciones externas. |
| B3-AC-15 | Eventos conocidos tienen labels seguros y un `event_type` desconocido permanece visible sin inferir resultado. |
| B3-AC-16 | El polling se programa 1.5 segundos después de finalizar el ciclo anterior y nunca se solapa. |
| B3-AC-17 | La pestaña oculta pausa nuevos ciclos y al volver visible se reanuda con el mismo cursor. |
| B3-AC-18 | El polling se detiene solo cuando el detalle es terminal y todos sus eventos anunciados fueron drenados. |
| B3-AC-19 | Requests y timers se cancelan al desmontar o cambiar `runId`. |
| B3-AC-20 | Un error posterior conserva el último snapshot válido y “Volver a intentar actualización” repite solo lecturas. |
| B3-AC-21 | Un run fallido muestra únicamente error seguro, código y correlation ID; nunca internals. |
| B3-AC-22 | El retry aparece si y solo si `status=failed` y `retryable=true`. |
| B3-AC-23 | Cada intención de retry usa una clave nueva, estable y ligada al run original. |
| B3-AC-24 | Doble clic y replay de transporte no crean más de un nuevo intento lógico. |
| B3-AC-25 | Una recarga con retry incierto requiere continuación explícita y reutiliza la misma clave. |
| B3-AC-26 | `IDEMPOTENCY_CONFLICT` no rota la clave y `RUN_NOT_RETRYABLE` retira el control tras refrescar. |
| B3-AC-27 | Un retry aceptado navega con `replace` al nuevo run, que enlaza al original mediante `retry_of_run_id`. |
| B3-AC-28 | Ningún flujo llama `getResult` ni muestra contenido asignado al Bloque 4. |
| B3-AC-29 | La experiencia funciona por teclado, mantiene foco visible y no tiene overflow horizontal desde 360 px. |
| B3-AC-30 | El navegador usa solo el proxy same-origin y no recibe secretos ni URLs internas. |
| B3-AC-31 | Las 43 pruebas del baseline y las nuevas pruebas del bloque pasan mediante `make check-web`. |
| B3-AC-32 | `git diff --check` termina correctamente y el diff no contiene cambios backend ni dependencias nuevas. |

Estos criterios aportan evidencia específica para S3-AT-006 a S3-AT-008,
S3-AT-011, S3-AT-013 a S3-AT-015, S3-AT-017, S3-AT-018 y S3-AT-022. No
cierran Sprint 3 ni sustituyen el resultado comercial o el E2E del Bloque 5.

## Matriz de evidencia de cierre

La evidencia automatizada se ejecuta con `make check-web`. Los nombres entre
comillas corresponden a casos o grupos de pruebas versionados en esta misma PR.

| Criterio | Evidencia |
|---|---|
| B3-AC-01 | `tests/components.test.tsx`, ruta inválida sin API |
| B3-AC-02 | `tests/run-observability.test.ts`, “hydrates detail first” |
| B3-AC-03 | `tests/run-workspace.test.tsx`, estados y metadatos de soporte |
| B3-AC-04 | `tests/run-workspace.test.tsx`, matriz de cinco estados textuales |
| B3-AC-05 | `tests/run-workspace.test.tsx`, retry ausente en `needs_review`; inspección visual 1440/360 px |
| B3-AC-06 | `tests/run-observability.test.ts`, hidratación desde cursor cero y `EVENT_PAGE_SIZE` |
| B3-AC-07 | `tests/run-observability.test.ts`, reanudación con último cursor confirmado |
| B3-AC-08 | `tests/run-observability.test.ts`, acumulación, replay idéntico, conflicto y hueco |
| B3-AC-09 | `tests/run-observability.test.ts`, drenaje secuencial de 101 eventos |
| B3-AC-10 | `tests/run-observability.test.ts`, códigos de error de contrato y estado estable recuperable |
| B3-AC-11 | `tests/run-observability.test.ts`, agrupación exclusivamente consecutiva |
| B3-AC-12 | `tests/run-observability.test.ts`, doce pasos y fallback desconocido |
| B3-AC-13 | `tests/run-workspace.test.tsx`, tool pública y payload no renderizado |
| B3-AC-14 | `tests/run-workspace.test.tsx`, acción interna diferenciada |
| B3-AC-15 | `tests/run-workspace.test.tsx`, evento desconocido visible y seguro |
| B3-AC-16 | `tests/run-observability.test.ts`, coordinador real: espera 1.5 s y cero solapamiento |
| B3-AC-17 | `tests/run-observability.test.ts`, coordinador real: pausa, visibilidad y mismo cursor |
| B3-AC-18 | `tests/run-observability.test.ts`, coordinador real: terminal drenado sin timers posteriores |
| B3-AC-19 | `tests/run-observability.test.ts`, coordinador real: aborto y eliminación del timer |
| B3-AC-20 | `tests/run-observability.test.ts`, coordinador real: error y recuperación manual desde el cursor estable |
| B3-AC-21 | `tests/run-workspace.test.tsx`, error público y correlation ID sin internals |
| B3-AC-22 | `tests/run-workspace.test.tsx`, matriz `failed && retryable` |
| B3-AC-23 | `tests/run-workspace.test.tsx`, coordinador real: UUID estable y registro persistido |
| B3-AC-24 | `tests/run-workspace.test.tsx`, coordinador real: guardia síncrona contra doble clic |
| B3-AC-25 | `tests/run-workspace.test.tsx`, coordinador real: continuación explícita con la misma clave |
| B3-AC-26 | `tests/run-workspace.test.tsx`, conflicto definitivo y `RUN_NOT_RETRYABLE` con refresh |
| B3-AC-27 | `tests/run-workspace.test.tsx`, `navigate` con replace al aceptado y enlace al original |
| B3-AC-28 | `tests/run-workspace.test.tsx` y revisión de alcance: sin `getResult` ni campos comerciales |
| B3-AC-29 | Prueba de foco de error; revisión manual real a 1440 px y 360 px, teclado y sin overflow |
| B3-AC-30 | `tests/client.test.ts`, `tests/proxy.test.ts` y revisión del cliente same-origin |
| B3-AC-31 | `make check-web`: 43 pruebas del baseline y 57 del Bloque 3 |
| B3-AC-32 | `git diff --check` y revisión de paths: frontend/documentación, sin dependencias ni backend |

El coordinador de polling probado es el mismo que instancia `RunWorkspace`; los
efectos de React se limitan a conectarlo con visibilidad, estado y cleanup. El
coordinador de retry probado es igualmente el usado por la UI y cubre la
exclusión mutua global: una intención perteneciente a otro run bloquea nuevas
mutaciones hasta volver al run propietario o descartarla explícitamente.

## Riesgos y mitigaciones

| Riesgo | Nivel | Mitigación |
|---|---:|---|
| Dos efectos o timers crean polling duplicado | Alto | Operación única, guardia `inFlight`, cleanup y pruebas con Strict Mode |
| La transición terminal pierde el último evento | Alto | Refrescar detalle, drenar hasta `last_event_sequence` y usar `terminal` como señal de relectura |
| Un hueco se oculta al deduplicar | Alto | Cursor contiguo; no avanzar ante salto o conflicto |
| Pestaña oculta genera carga inútil | Medio | Visibility API y reanudación inmediata con el mismo cursor |
| Error transitorio borra la evidencia ya vista | Alto | Snapshot inmutable y estado degradado separado |
| Retry duplica runs por timeout o doble clic | Alto | Guardia síncrona, intención persistida y clave estable |
| Retry aparece para revisión humana | Alto | Render condicionado exclusivamente por `failed && retryable` |
| Timeline parece log técnico | Alto | Labels cerrados, agrupación por paso y detalles técnicos secundarios |
| UI confunde acciones internas con integraciones reales | Alto | Labels “demo”/“acción interna” y ausencia de promesas externas |
| Evento nuevo rompe el mapper | Medio | Fallback visible sin inferir semántica |
| Contrato narrativo induce a usar `summary` inexistente | Alto | Schema efectivo documentado y tests de allowlist |
| Bloque 4 entra mediante `getResult` | Alto | Prohibición explícita y test de ausencia |
| La timeline crece en una versión futura | Bajo en MVP | Bounded orchestration actual; revisar virtualización solo con evidencia posterior |
| README induce a un baseline incorrecto | Medio | Baseline fijado por commit y corrección documental diferida al cierre |

## Archivos afectados previstos

### Nuevo documento

- `docs/implementation/072-sprint-3-block-3-run-observability.md`.

### Implementación prevista después de aprobación

Nuevos, con nombres ajustables sin cambiar responsabilidades:

- `apps/web/src/components/run-workspace.tsx`;
- `apps/web/src/components/run-timeline.tsx`;
- `apps/web/src/lib/run-observability.ts`;
- `apps/web/tests/run-observability.test.ts`;
- `apps/web/tests/run-workspace.test.tsx`.

Modificados:

- `apps/web/src/app/runs/[runId]/page.tsx`;
- `apps/web/src/lib/api/client.ts`, exclusivamente para aceptar
  `AbortSignal` opcional en `getRun`, `getEvents` y `retryRun`, sin cambiar
  rutas, query, headers, payloads ni respuestas HTTP;
- `apps/web/src/app/globals.css`;
- `apps/web/tests/components.test.tsx`, solo para sustituir expectativas del
  placeholder del Bloque 2;
- `apps/web/tests/client.test.ts`, solo si falta evidencia de paths, query o
  header ya implementados.

No se prevén cambios en:

- `apps/web/src/lib/api/types.ts`;
- `apps/api/`;
- `package.json` o `package-lock.json`;
- Docker Compose, CI, variables de entorno o migraciones;
- README, CHANGELOG o documentos de los Bloques 4 y 5.

Si durante implementación un contrato existente resulta insuficiente, se
detiene el bloque y se actualiza la documentación antes de autorizar un delta.

El ajuste de `AbortSignal` anterior queda incorporado a esta especificación
como detalle interno necesario para cumplir B3-AC-19. No amplía el contrato
HTTP ni el alcance funcional del bloque.

## Definition of Done del Bloque 3

### Funcional

- B3-AC-01 a B3-AC-32 tienen evidencia;
- el placeholder fue reemplazado por datos reales de detalle y eventos;
- polling incremental, terminalidad y recuperación funcionan según este
  documento;
- la timeline identifica tools y acciones internas sin mostrar payloads crudos;
- los tres estados terminales son inequívocos;
- retry es auditable, idempotente y crea un run distinto;
- el run nuevo enlaza al original;
- no se consulta ni renderiza `RunResult`.

### Técnica

- no existen requests solapados, timers huérfanos ni actualizaciones después de
  desmontar;
- el cursor solo avanza por secuencias válidas y contiguas;
- no se añadieron dependencias ni estado global;
- TypeScript estricto, lint, tests y build incluidos en `make check-web` pasan;
- las 43 pruebas previas siguen aprobadas;
- `git diff --check` pasa;
- no hay cambios backend, secretos, URLs internas ni acceso directo a FastAPI.

### UX y accesibilidad

- navegación por teclado y foco visible verificados;
- layout verificado a 360 px y escritorio;
- estados no dependen solo del color;
- polling silencioso no produce anuncios repetitivos;
- error de retry recibe foco y tiene mensaje seguro;
- `needs_review` no se confunde con fallo;
- timeline comprensible sin JSON y sin conocimiento técnico del backend.

### Documental

- esta especificación fue aprobada antes del código y queda versionada en la
  PR de implementación;
- la PR de implementación enlaza cada B3-AC a test o evidencia manual;
- riesgos residuales y desviaciones quedan documentados;
- el estado desactualizado del README se registra para el cierre documental sin
  ampliar la implementación de este bloque.

## Condición de cierre

El Bloque 3 se declara cerrado únicamente después de:

1. aprobar esta especificación antes de programar y versionarla en el
   repositorio;
2. implementar sin cambios backend ni alcance del Bloque 4;
3. completar B3-AC-01 a B3-AC-32;
4. ejecutar los gates y la evidencia manual;
5. fusionar la implementación;
6. sincronizar `main` y revalidar `make check-web`.

Hasta entonces, `RunResult` y el workspace comercial permanecen bloqueados para
implementación.
