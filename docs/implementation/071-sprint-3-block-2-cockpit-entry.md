# Sprint 3 — Bloque 2: cockpit y entrada

## Estado

- **Estado:** Proposed for approval
- **Baseline:** `6056aabe674744b3f0bacb4220f086f371ccf834`
- **Baseline documental:** PR #14, fusionado en
  `8ebf0b29be9e4aa81605d090c259c5a4823f724f`
- **Baseline de implementación:** PR #15
- **Rama prevista:** `feat/sprint3-inquiry-entry`
- **Objetivo único:** permitir que una persona abra una ejecución real desde
  el cockpit, mediante entrada manual o UC-001, sin terminal ni Swagger.

Este documento concreta exclusivamente el Bloque 2 de
`068-sprint-3-implementation-plan.md`. Mantiene los contratos de Sprint 2 y la
fundación web del Bloque 1; no autoriza trabajo de los Bloques 3–5 ni cambios
backend.

## Resultado observable

Al terminar el bloque:

1. `/` muestra los runs recientes reales, con carga, vacío y error explícitos;
2. cada run listado abre `/runs/[runId]`;
3. `/inquiries/new` permite escribir una consulta o cargar la entrada UC-001;
4. una sola acción crea primero la inquiry y después su agent run;
5. ambos comandos usan claves idempotentes independientes y estables;
6. doble clic y replay de transporte no duplican inquiry, run ni enqueue;
7. tras aceptar el run, la aplicación navega a `/runs/[runId]`;
8. la experiencia funciona con teclado y desde 360 px.

El workspace de destino solo necesita existir como punto de llegada acotado:
puede mostrar el identificador del run y un mensaje de que su observabilidad se
incorpora en el Bloque 3. No consulta estado, eventos ni resultado.

## Fuentes de verdad y contratos consumidos

La implementación debe derivarse de:

- la planificación fusionada en PR #14;
- `031-frontend-experience.md`;
- los schemas Pydantic y endpoints actuales de `apps/api`;
- los tipos y el cliente centralizado creados en Bloque 1;
- el seed demo y el escenario UC-001 vigentes.

No se duplican tipos HTTP ni se llama a FastAPI directamente. El navegador usa
exclusivamente el proxy same-origin y estas operaciones ya disponibles:

| Operación | Contrato efectivo | Uso en Bloque 2 |
|---|---|---|
| Listar runs | `GET /api/v1/agent-runs?limit=20&offset=0` | Cockpit, en el orden estable del backend |
| Crear inquiry | `POST /api/v1/inquiries` | Entrada manual o demo, con `Idempotency-Key` |
| Crear run | `POST /api/v1/inquiries/{inquiry_id}/agent-runs` | Segundo comando, con otra `Idempotency-Key` |

`AgentRunSummary` es la única fuente del listado. Expone `id`, `inquiry_id`,
`status`, `current_step`, `company_name`, `market`, `received_at`, `started_at`,
`completed_at`, `error_code`, `retryable` y `retry_of_run_id`. Los valores
nulos se presentan como no disponibles; la UI no intenta reconstruir empresa
o mercado consultando otras entidades.

`InquiryCreate.raw_message` admite entre 1 y 10 000 caracteres después de
trim. `source` solo puede ser `manual` o `demo`, y `customer_id` es opcional.
El frontend replica estos límites para respuesta inmediata, pero el backend
continúa siendo autoritativo.

## Cockpit `/`

### Composición

La página sustituye el contenido temporal de fundación y contiene:

- título y contexto breve del modo demo;
- CTA principal “Nueva consulta” hacia `/inquiries/new`;
- una región “Ejecuciones recientes”;
- hasta 20 runs retornados por `api.listRuns({ limit: 20, offset: 0 })`;
- un enlace inequívoco por item hacia `/runs/{id}`.

No se añaden filtros, búsqueda, ordenamiento local, paginación, tabla de
inquiries, métricas ni acciones sobre runs. El orden recibido del backend se
conserva.

Cada item muestra, solo cuando el contrato lo permite:

- estado con texto y no solo color;
- empresa o “Empresa no disponible”;
- mercado o “Mercado no disponible”;
- fecha de recepción formateada para la locale de la interfaz;
- acceso “Abrir ejecución”.

La tarjeta completa puede ser enlace siempre que conserve nombre accesible,
foco visible y estructura semántica. `current_step`, error y retry no se
desarrollan como experiencia de observabilidad en este bloque.

### Estados

| Estado | Tratamiento |
|---|---|
| Carga | Skeleton o texto visible dentro de una región con estado anunciable; no muestra datos ficticios |
| Con datos | Lista semántica de items reales |
| Vacío | Explica que aún no hay ejecuciones y ofrece “Crear primera consulta” |
| Error | Mensaje seguro, correlation ID si existe y control para volver a intentar la lectura |

El error no elimina el CTA de nueva consulta. La recuperación repite solo el
GET y nunca dispara una mutación.

## Entrada `/inquiries/new`

### Formulario manual

El formulario contiene:

- label asociado al textarea;
- ayuda breve sobre el tipo de consulta admitida;
- contador o indicación del máximo de 10 000 caracteres;
- acción secundaria “Cargar escenario UC-001”;
- nota visible de que se opera con datos demo;
- submit único “Crear consulta y ejecutar agente”;
- región anunciable para progreso o error.

Una entrada manual envía:

```json
{
  "source": "manual",
  "raw_message": "<mensaje normalizado>",
  "customer_id": null
}
```

El submit se rechaza localmente cuando el contenido normalizado está vacío o
supera 10 000 caracteres. El foco se mueve al primer error y el mensaje se
asocia al control. Los errores de API usan `ApiError.message` y, cuando existe,
`correlationId`; nunca muestran internals.

### Escenario UC-001

La acción de carga rellena el formulario con la entrada canónica vigente:

> We need 600 bottles of Albariño for specialised wine shops in Germany.
> Recommend two references.

Además selecciona como dato de entrada el customer demo existente
`aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1` (`Rhein Selection GmbH`) y usa
`source: "demo"`. Esta asociación permite ejercer el contexto y la memoria del
escenario ya sembrado. El identificador se mantiene en una constante de demo,
no se presenta como selector general de clientes.

Cargar UC-001 no envía el formulario. El usuario puede revisar o editar el
mensaje. Si lo edita, la intención pasa a manual: `source` cambia a `manual` y
`customer_id` vuelve a `null`, para no atribuir texto arbitrario al cliente
demo. Volver a cargar UC-001 restaura exactamente su entrada.

No se incluyen recomendaciones, stock, precios, artefactos ni resultados
esperados en el frontend. Esos datos solo podrán proceder del backend en el
Bloque 4.

## Flujo inquiry → agent run

El submit es una máquina local de etapas, no dos acciones visibles:

```text
idle → creating_inquiry → creating_run → navigating
                    ↘ recoverable_error ↗
```

1. normalizar y congelar el payload de la intención;
2. generar `inquiryKey` y `runKey` independientes con
   `crypto.randomUUID()`;
3. persistir la intención pendiente antes del primer POST;
4. llamar `api.createInquiry(payload, inquiryKey)`;
5. guardar el `inquiry.id` devuelto;
6. llamar `api.createRun(inquiry.id, runKey)`;
7. guardar el `agent_run_id` aceptado;
8. navegar con reemplazo a `/runs/{agent_run_id}`;
9. limpiar la intención pendiente después de disponer del destino.

No se navega a una ruta de inquiry intermedia. Una respuesta `200` al replay de
la inquiry y una respuesta `202` del run son resultados válidos del mismo
flujo.

## Idempotencia, replay y doble envío

### Registro de intención

Se conserva un único registro versionado en `sessionStorage`, limitado a la
pestaña y sin datos sensibles adicionales:

```text
version, payload, inquiryKey, runKey, stage, inquiryId?, runId?
```

El registro permite continuar después de un error de transporte o recarga
accidental. No es una cola ni estado global de negocio. Solo se recupera cuando
su payload coincide exactamente con el formulario congelado; cambiar el
mensaje o cargar de nuevo el escenario crea una intención nueva con claves
nuevas.

Las claves:

- son ASCII seguras y menores al límite backend de 160 caracteres;
- nunca se reutilizan entre inquiry y run;
- no cambian por timeout, desconexión ni respuesta ilegible;
- permanecen asociadas al mismo payload y, para el run, al mismo inquiry;
- se descartan solo al completar la navegación, cancelar explícitamente la
  intención o recibir un error definitivo que requiera corrección del usuario.

Un error de transporte en `creating_inquiry` repite el primer POST con el mismo
payload y `inquiryKey`. Si ya existe `inquiryId`, la recuperación no recrea la
inquiry: repite directamente el POST del run con el mismo `runKey`. Esto cubre
incluido el caso en que el backend persiste el run pero la respuesta se pierde.

`IDEMPOTENCY_CONFLICT` se presenta como error definitivo y no se sortea
automáticamente generando otra clave. Una nueva intención explícita sí genera
un par nuevo. Otros errores de dominio conservan mensaje seguro y correlation
ID; el usuario puede corregir o iniciar una intención nueva según el caso.

### Prevención de doble submit

La protección combina:

- guardia síncrona antes de cualquier `await`;
- un solo handler de submit en el formulario;
- botón deshabilitado y `aria-disabled` durante todas las etapas activas;
- label de progreso que distingue “Creando consulta” y “Iniciando agente”;
- reutilización del mismo registro aunque dos eventos alcancen el handler.

Deshabilitar el botón mejora la UX, pero la garantía final procede de las dos
claves y de los contratos idempotentes del backend.

## Navegación

- la cabecera conserva enlaces válidos a “Cockpit” y “Nueva consulta”;
- el CTA del cockpit abre `/inquiries/new`;
- cancelar o volver desde la entrada regresa a `/` sin mutar datos;
- cada item del cockpit abre `/runs/[runId]`;
- el run recién aceptado usa `router.replace`, evitando que “atrás” reenvíe el
  formulario;
- la ruta de destino valida la forma del identificador solo para presentación,
  sin consultar detalle, eventos o resultado en este bloque.

No se introducen rutas adicionales ni enlaces a superficies inexistentes.

## Accesibilidad y responsive

- landmarks, jerarquía de headings y listas semánticas;
- skip link y foco visible heredados del shell;
- labels y descripciones asociados al textarea;
- errores conectados mediante `aria-describedby`;
- progreso y errores en región `role="status"` o `aria-live`, sin anuncios
  repetitivos;
- foco administrado al error de validación y al resumen de error del servidor;
- estado expresado con texto e icono, nunca solo con color;
- controles alcanzables y activables por teclado;
- targets de interacción adecuados y orden de foco coherente;
- tarjetas apiladas y formulario sin scroll horizontal desde 360 px;
- `prefers-reduced-motion` respetado para cualquier transición no esencial.

El foco no se mueve durante una carga correcta que terminará en navegación.

## Estrategia de pruebas

### Unitarias

- normalización y validación del mensaje;
- construcción de payload manual y UC-001;
- cambio de demo a manual al editar;
- generación de dos claves distintas y seguras;
- reducer o máquina de etapas de la intención;
- serialización, recuperación y descarte del registro pendiente;
- formatos y fallbacks del resumen de run.

### Componentes y rutas

- cockpit con carga, lista, vacío y error;
- links correctos para CTA y runs;
- formulario, labels, validación y carga de UC-001;
- submit deshabilitado y progreso anunciado;
- error seguro con correlation ID;
- workspace placeholder sin polling ni lectura comercial;
- navegación por teclado y comprobaciones automáticas de accesibilidad.

### Integración del flujo

- `listRuns` se invoca con paginación acotada;
- create inquiry precede a create run;
- el segundo endpoint recibe el ID devuelto por el primero;
- inquiry y run reciben claves diferentes;
- doble clic produce un POST lógico por etapa;
- timeout al crear inquiry repite payload y clave;
- timeout al crear run conserva inquiry, parent y clave;
- replay que devuelve el recurso existente navega al mismo run;
- `IDEMPOTENCY_CONFLICT` no rota claves automáticamente;
- aceptar el run hace `replace` hacia `/runs/[runId]`.

Las pruebas frontend usan respuestas contractuales controladas. Puede añadirse
una prueba de integración con FastAPI real si cabe en el bloque, pero el E2E
completo con backend determinista, polling y resultado pertenece al Bloque 5.
No se requiere Qwen live.

### Gates del bloque

```bash
make check-web
git diff --check
```

La suite backend no necesita cambios; si la implementación toca accidentalmente
un contrato compartido, `make check-api` debe seguir pasando y el cambio queda
fuera de este bloque hasta documentarse.

## Riesgos y mitigaciones

| Riesgo | Nivel | Mitigación |
|---|---:|---|
| Doble clic crea comandos duplicados | Alto | Guardia síncrona, UI bloqueada e idempotencia backend |
| Se pierde la respuesta entre ambas etapas | Alto | Registro por etapas y replay con las mismas claves |
| Una recarga rota la intención | Medio | Persistencia acotada en `sessionStorage` |
| Una clave se reutiliza con otro payload o parent | Alto | Payload congelado y claves ligadas a la intención |
| Cockpit inventa empresa o mercado | Alto | Renderizar solo `AgentRunSummary` y fallbacks explícitos |
| UC-001 hardcodea resultados | Alto | Constante solo de entrada; todo resultado queda fuera |
| El cliente demo sembrado no existe | Medio | Mostrar `CUSTOMER_NOT_FOUND` seguro; no crear cliente ni fallback backend |
| El placeholder adelanta observabilidad | Medio | Sin fetch, polling, timeline, retry ni resultado |
| Error técnico expone internals | Alto | `ApiError` seguro y correlation ID solamente |
| La lista crece hacia CRM | Alto | 20 runs, sin filtros, métricas ni mutaciones |

## Fuera de alcance

- polling, consulta incremental o estado vivo del run;
- timeline, eventos, tools o traducción de pasos;
- resultados comerciales, análisis, recomendación, stock, quote, artefactos,
  oportunidad, seguimiento o memoria;
- retry de runs fallidos;
- autenticación, roles, usuarios o multitenencia operativa;
- integraciones externas, envío de correo, CRM, calendario, ERP o inventario;
- aprobación, rechazo, edición, reserva o sincronización;
- filtros, búsqueda, paginación visual, analytics o dashboard de métricas;
- librería de estado global;
- endpoints, schemas, migraciones, modelos, repositorios, servicios, prompts,
  tools, orquestación o cualquier otro cambio backend.

## Archivos afectados previstos

### Nuevos

- `apps/web/src/app/inquiries/new/page.tsx`;
- `apps/web/src/app/runs/[runId]/page.tsx`;
- `apps/web/src/app/loading.tsx`;
- `apps/web/src/app/error.tsx`;
- componentes acotados de cockpit y formulario bajo `apps/web/src/components/`;
- utilidades de UC-001 e intención idempotente bajo `apps/web/src/lib/`;
- pruebas correspondientes bajo `apps/web/tests/`;
- `docs/implementation/071-sprint-3-block-2-cockpit-entry.md`.

### Modificados

- `apps/web/src/app/page.tsx`;
- `apps/web/src/app/layout.tsx`, solo si la navegación existente requiere los
  nuevos enlaces;
- `apps/web/src/app/globals.css`;
- configuración de pruebas frontend solo si es imprescindible para DOM o
  accesibilidad.

La lista es una previsión de implementación, no autorización para modificar
archivos backend, dependencias de runtime, Compose, CI, README o documentación
de bloques posteriores.

## Criterios de aceptación del bloque

| ID | Criterio verificable |
|---|---|
| B2-AC-01 | `/` lista hasta 20 runs reales en el orden del backend. |
| B2-AC-02 | Cada item muestra estado, empresa, mercado y fecha con fallbacks para nulos. |
| B2-AC-03 | El cockpit trata explícitamente carga, vacío y error. |
| B2-AC-04 | El CTA de nueva consulta permanece disponible incluso si falla el listado. |
| B2-AC-05 | Cada run enlaza a `/runs/[runId]` con nombre accesible. |
| B2-AC-06 | `/inquiries/new` admite un mensaje manual válido de 1 a 10 000 caracteres normalizados. |
| B2-AC-07 | Vacío, whitespace y exceso de longitud se rechazan con error asociado y foco. |
| B2-AC-08 | Cargar UC-001 rellena entrada y cliente demo, pero no envía ni carga resultados. |
| B2-AC-09 | Editar UC-001 convierte el payload en manual y elimina la asociación al cliente demo. |
| B2-AC-10 | Un submit crea inquiry y luego run mediante el cliente same-origin existente. |
| B2-AC-11 | Las dos operaciones reciben claves idempotentes independientes. |
| B2-AC-12 | Cada clave permanece estable durante replays de transporte de su etapa. |
| B2-AC-13 | Tras crear la inquiry, recuperar el flujo no vuelve a crearla y conserva el mismo parent del run. |
| B2-AC-14 | Doble clic no genera más de una intención ni duplica recursos. |
| B2-AC-15 | `IDEMPOTENCY_CONFLICT` se muestra y no provoca rotación automática de clave. |
| B2-AC-16 | El progreso distingue creación de inquiry e inicio del agente. |
| B2-AC-17 | Errores muestran mensaje seguro y correlation ID disponible, sin internals. |
| B2-AC-18 | Un run aceptado navega con `replace` a `/runs/[runId]`. |
| B2-AC-19 | El destino de run de este bloque no hace polling ni consulta eventos o resultado. |
| B2-AC-20 | Cockpit y entrada funcionan por teclado, tienen foco visible y no dependen solo de color. |
| B2-AC-21 | El flujo no presenta scroll horizontal desde 360 px. |
| B2-AC-22 | El navegador no accede directamente a FastAPI ni recibe secretos. |
| B2-AC-23 | No existen controles o datos que prometan funciones de bloques posteriores. |
| B2-AC-24 | `make check-web` y `git diff --check` terminan correctamente. |

Estos criterios aportan evidencia parcial para S3-AT-002 a S3-AT-005,
S3-AT-015, S3-AT-017 y S3-AT-018. No cierran Sprint 3 ni sustituyen el E2E y
las evidencias integradas del Bloque 5.

## Condición de cierre

El Bloque 2 solo puede declararse cerrado después de:

1. aprobar este documento antes de implementar producto;
2. completar B2-AC-01 a B2-AC-24 con evidencia;
3. confirmar que el diff no contiene cambios backend ni alcance de Bloques 3–5;
4. ejecutar los gates documentados;
5. fusionar la implementación y revalidarla en `main`.

Hasta entonces, polling, timeline y resultados comerciales permanecen
bloqueados para implementación.
