# Sprint 3 — Bloque 4: resultados comerciales

## Estado

- **Estado:** Propuesta para aprobación
- **Baseline de código y documentación:**
  `main@fd04479810580d3054a78474cca5fd89613267c2`
- **Baseline funcional:** Sprint 3, Bloque 3 fusionado mediante PR #18
- **Verificación declarada del baseline:** ESLint, TypeScript, 100 pruebas web
  y build de producción aprobados
- **Rama de implementación prevista:** `feat/sprint3-commercial-result`
- **Objetivo único:** convertir el `RunResult` terminal existente en una
  superficie de revisión comercial comprensible, segura y parcial-tolerante,
  sin modificar el backend ni repetir el cockpit o la observabilidad del
  Bloque 3.

Este documento concreta exclusivamente el Bloque 4 definido en
`068-sprint-3-implementation-plan.md`. Es documentación de planificación: no
autoriza código antes de su aprobación y fusión.

## Fuentes de verdad y resolución de discrepancias

La futura implementación debe derivarse, en este orden, de:

1. los schemas Pydantic y endpoints vigentes en
   `apps/api/app/api/schemas.py` y `apps/api/app/api/v1/product.py`;
2. los contratos de dominio de análisis, recomendación, cotización y
   artefactos en `apps/api/app/domain/`;
3. los tipos y el cliente same-origin de `apps/web/src/lib/api/`;
4. `067-sprint-3-charter.md`;
5. `068-sprint-3-implementation-plan.md`;
6. `069-sprint-3-acceptance-and-definition-of-done.md`;
7. `031-frontend-experience.md`;
8. `072-sprint-3-block-3-run-observability.md`.

Cuando un texto narrativo antiguo difiera del contrato efectivo, prevalece el
schema Pydantic de la baseline. La UI presenta únicamente datos recibidos y
validados; no completa, calcula ni infiere valores comerciales ausentes.

## Resultado observable

Al terminar el bloque, una persona puede:

1. revisar el mensaje original y los datos extraídos;
2. identificar la información faltante sin confundirla con un error técnico;
3. comprender qué productos se recomiendan y qué stock vendible respaldó la
   recomendación;
4. revisar una cotización en EUR, sus líneas y sus supuestos explícitos;
5. leer una propuesta y un correo marcados como borradores generados por IA;
6. copiar la propuesta, el asunto o el cuerpo del correo como texto plano;
7. distinguir datos de entrada, datos de catálogo y reglas deterministas de
   texto generado por IA;
8. ver oportunidad, seguimiento y memoria demo cuando estén disponibles;
9. seguir usando las secciones válidas si una sección falta o es incompatible;
10. reconocer con claridad los estados `success`, `needs_review`, `failed` y
    `unavailable` después de la carga del resultado.

El Bloque 4 añade una región de resultado debajo del workspace ya existente.
No rediseña la cabecera, la timeline, el polling, el retry ni los estados de
ejecución implementados en el Bloque 3.

## Alcance

### Funcional

- solicitar `RunResult` solo cuando el detalle indique un estado terminal;
- presentar carga, resultado correcto, revisión humana, fallo parcial y
  resultado no disponible;
- mostrar mensaje original, análisis e información faltante;
- presentar recomendación validada y evidencia de stock incluida en ella;
- presentar cotización determinista y sus supuestos;
- reconocer y mostrar artefactos `proposal` y `email_draft` versión `1.0`;
- separar visual y semánticamente contenido determinista y texto generado;
- presentar registros demo de cliente, oportunidad, seguimiento y memoria;
- conservar y etiquetar warnings sin convertirlos en errores técnicos;
- aislar datos ausentes, parciales, desconocidos o incompatibles por sección;
- copiar únicamente representaciones de texto plano construidas con contenido
  visible y validado;
- mantener accesibilidad y comportamiento responsive desde 360 px.

### Técnica

- usar `api.getResult(runId)` y el proxy same-origin existentes;
- añadir, durante la implementación, cancelación opcional mediante
  `AbortSignal` al método frontend sin alterar la ruta HTTP;
- conservar `RunResult` como envelope HTTP y validar sus objetos opacos en un
  adapter frontend separado;
- usar guards cerrados por `schema_version` y `artifact_type`;
- construir view models discriminados; los componentes no acceden a JSON
  opaco directamente;
- formatear importes y fechas para presentación sin ejecutar reglas de negocio;
- no añadir dependencias runtime, librería de estado, markdown ni sanitizador
  HTML;
- no persistir el resultado ni el contenido copiado en almacenamiento del
  navegador.

## Exclusiones

Queda fuera de alcance:

- cualquier cambio en `apps/api`, OpenAPI o contratos HTTP;
- autenticación, roles, multitenencia o permisos;
- edición, aprobación, rechazo o versionado persistente de artefactos;
- envío de correo o integración con proveedor de email;
- CRM, calendario, ERP, inventario, stock o logística externos;
- reserva o modificación de stock;
- generación o descarga de PDF;
- exportación a Word, CSV u otro formato;
- links de pago, firma, impuestos, transporte, seguros, aranceles o aduanas;
- recalcular cotizaciones, corregir cantidades o sustituir productos;
- regenerar propuesta, correo, recomendación o análisis;
- convertir el workspace en editor, CRM o catálogo;
- nuevas rutas o navegación principal;
- repetir la timeline, tools, acciones internas, correlation ID o retry del
  Bloque 3;
- métricas, analítica, búsqueda, filtros o comparación entre runs;
- render de markdown, HTML generado, URLs externas o archivos adjuntos;
- nuevos prompts, modelos, tools, reglas comerciales u orquestación;
- E2E completo y cierre de Sprint 3, reservados para el Bloque 5.

## Contrato efectivo de `RunResult`

### Endpoint y disponibilidad

El cliente ya encapsula:

```text
GET /api/v1/agent-runs/{agent_run_id}/result
```

El endpoint:

- devuelve `404 AGENT_RUN_NOT_FOUND` si el run no existe;
- devuelve `409 RUN_NOT_TERMINAL` si el run aún no es terminal;
- devuelve `404 INQUIRY_NOT_FOUND` si falta la inquiry asociada;
- admite `completed`, `needs_review` y `failed` como estados terminales;
- puede devolver secciones nulas o colecciones vacías en un resultado parcial.

El Bloque 4 no usa `result_url` para construir una llamada dinámica ni accede
directamente a FastAPI. Usa el método tipado y la ruta same-origin fija.

### Campos superiores

| Campo | Tipo efectivo | Uso de presentación |
|---|---|---|
| `agent_run_id` | UUID | Verificar que coincide con la ruta; no duplicar la cabecera |
| `status` | Estado del run | Seleccionar `success`, `needs_review` o `failed` |
| `inquiry` | `InquiryDetail` | Mensaje original, idioma y faltantes |
| `analysis` | objeto o `null` | Datos estructurados extraídos |
| `recommendation` | objeto o `null` | Recomendación validada y stock |
| `quote` | `QuotePublic` o `null` | Cotización y supuestos deterministas |
| `artifacts` | lista | Propuesta, correo y artefactos incompatibles |
| `customer` | objeto o `null` | Contexto de cliente demo |
| `opportunity` | objeto o `null` | Registro de oportunidad demo |
| `followup` | objeto o `null` | Seguimiento demo |
| `memory_summary` | lista | Hechos persistidos del cliente |
| `warnings` | lista de texto | Advertencias globales del resultado |

### Brecha contractual identificada

El backend expone `analysis`, `recommendation`, `QuotePublic.assumptions` y
`ArtifactPublic.content` como `dict[str, object]`. El cliente TypeScript
representa estas cuatro zonas como `JsonObject`, por lo que no puede acceder de
forma segura a sus campos solo con tipado estático.

Además, `apiRequest<T>` devuelve el payload mediante un cast TypeScript sin
validación runtime. El adapter superior debe validar el envelope de
`RunResult`, incluidos `agent_run_id`, `status`, `inquiry`, colecciones y
entidades tipadas, antes de ejecutar los guards versionados de cada sección.

Esta brecha no exige modificar el backend para UC-001. La futura implementación
debe resolverla en frontend mediante guards versionados que:

- acepten únicamente las formas `1.0` ya definidas en el dominio;
- produzcan view models tipados;
- rechacen una sección incompatible sin descartar el resto del `RunResult`;
- no hagan casts directos ni usen valores por defecto que parezcan datos
  recibidos.

No se crea ADR: es una adaptación local del cliente a un contrato existente,
sin nueva frontera de arquitectura ni cambio persistente.

### Análisis reconocido `1.0`

El adapter puede reconocer los campos vigentes de `InquiryAnalysis`:

- `language`, `intent`, `market`, `product_interest`;
- `estimated_bottles`, `channel`, `target_horizon_days`, `target_date`;
- `samples_requested`, `price_list_requested`;
- `budget_total_cents`, `budget_currency`;
- `sample_delivery_address`, `delivery_terms`;
- `certification_requirements`, `tax_identifier`;
- `company_name`, `contact_name`, `contact_email`.

`inquiry.missing_fields` es la fuente autoritativa de faltantes. La UI no vuelve
a ejecutar `compute_missing_fields`. Un código conocido recibe label en
español; uno futuro se muestra como “Dato pendiente no reconocido” junto con su
código, sin romper la sección.

### Recomendación reconocida `1.0`

La forma efectiva es `ValidatedRecommendation`:

- `schema_version="1.0"`;
- `items[]` con `product_id`, `sku`, `name`, `quantity_bottles`,
  `units_per_case`, `cases`, `unit_price_cents`, `sellable_bottles`,
  `certifications` y `rationale`;
- `total_bottles`, `currency="EUR"`, `summary`, `warnings` y
  `validation_status="valid"`.

`sellable_bottles` es la evidencia de stock disponible ya expuesta por el
resultado. No se necesita un nuevo campo `stock` ni otra llamada al backend.
La UI no afirma que el stock esté reservado y no calcula disponibilidad futura.

### Cotización efectiva

`QuotePublic` contiene:

- `id`, `currency="EUR"`, `subtotal_cents`, `status` y `assumptions`;
- líneas con producto, SKU, nombre, botellas, precio unitario, total y cajas.

Los importes son enteros en céntimos. La UI divide solo para formatear con
`Intl.NumberFormat`; no recalcula el subtotal, los totales de línea, las cajas
ni el presupuesto.

Los supuestos `1.0` que deben presentarse explícitamente son:

- precio procedente de la recomendación validada;
- impuestos no incluidos;
- transporte no incluido;
- seguro no incluido;
- aranceles y aduanas no incluidos;
- stock no reservado;
- revisión humana requerida.

Una clave futura no se interpreta. Puede causar que la lista de supuestos se
marque incompatible sin ocultar las líneas válidas de la cotización.

### Artefactos reconocidos `1.0`

`ArtifactPublic` aporta metadatos y un `content` opaco. Se reconocen:

| `artifact_type` | Contenido visible |
|---|---|
| `proposal` | Comprador, snapshot de quote, titular, resumen ejecutivo, posicionamiento por producto, próximos pasos, preguntas abiertas y warnings |
| `email_draft` | Destinatario, vínculo lógico a propuesta, bloque comercial, asunto, introducción, resumen, siguiente paso, preguntas, cierre y warnings |

El adapter exige coincidencia entre el tipo exterior, el tipo interior, la
versión y el `review_status`. Un artefacto futuro o inconsistente se presenta
como no compatible; nunca se renderiza su JSON crudo. Si existen varios
artefactos reconocidos del mismo tipo, se muestran por separado con fecha e ID
abreviado; no se elige uno silenciosamente.

## Modelo de procedencia y confianza

La procedencia no depende solo del color. Cada región usa label textual, icono
decorativo opcional y tratamiento visual consistente.

| Categoría | Contenido | Label vinculante |
|---|---|---|
| Entrada recibida | `inquiry.raw_message` y datos aportados | Consulta recibida |
| IA estructurada | Campos de `analysis` | Extraído por IA — revisar |
| IA validada | Selección, resumen y rationale de recomendación | Recomendación de IA validada por reglas |
| Dato autoritativo | SKU, nombre, precio y stock enriquecidos | Catálogo y stock del sistema demo |
| Determinista | Quote, totales y supuestos | Cálculo determinista |
| IA narrativa | Texto de propuesta y correo | Texto generado por IA — borrador |
| Persistencia demo | Cliente, oportunidad, seguimiento y memoria | Registro interno demo |

Una ejecución `completed` no convierte la propuesta o el correo en contenido
aprobado. Cada artefacto conserva “Borrador — requiere revisión humana” aunque
el run haya completado correctamente.

## Composición del resultado comercial

### Orden y jerarquía

La región “Resultado comercial” se añade después del estado y la timeline del
Bloque 3 y mantiene este orden:

1. resumen del resultado y warnings globales;
2. consulta, análisis y faltantes;
3. recomendación y stock;
4. cotización;
5. propuesta;
6. borrador de correo;
7. oportunidad y seguimiento demo;
8. memoria del cliente.

En escritorio, recomendación y cotización pueden usar dos columnas si cada
tabla conserva espacio legible. Propuesta y correo ocupan el ancho completo.
En móvil todo se presenta en una sola columna y las tablas usan contenedor con
scroll horizontal etiquetado; no reducen texto hasta hacerlo ilegible.

### Consulta, análisis y faltantes

- el mensaje original se presenta como texto preservando saltos de línea;
- no se interpreta como HTML ni markdown;
- el análisis usa pares label/valor y omite decoración para valores ausentes;
- `false` y `0` son valores válidos, no “sin datos”;
- importes, fechas, países e idiomas usan formato de presentación, conservando
  el valor técnico en un disclosure solo cuando sea útil;
- faltantes vacíos muestran “No se detectaron datos comerciales pendientes”;
- faltantes presentes se muestran como lista de aclaraciones requeridas;
- un análisis `null` no se sustituye por inferencias desde el mensaje.

### Recomendación y stock

- el resumen abre la sección con el label de IA validada;
- cada producto muestra nombre, SKU, cantidad, cajas, certificaciones y
  rationale;
- precio y `sellable_bottles` aparecen en un bloque autoritativo distinto del
  rationale;
- el stock se expresa como “Stock vendible observado: N botellas”;
- nunca se muestra “reservado”, “garantizado” o “disponible al enviar”;
- warnings propios permanecen dentro de la sección;
- no se deriva un nuevo estado de disponibilidad comparando cantidades en UI;
- `recommendation=null` produce estado de sección no disponible.

### Cotización determinista

- tabla con producto/SKU, botellas, cajas, precio unitario y total de línea;
- subtotal destacado, moneda EUR y estado del quote en texto;
- importes con formato de moneda y precisión de dos decimales;
- supuestos visibles cerca del subtotal, no ocultos solo en un disclosure;
- label “Cotización demo — no constituye oferta final”;
- no se añaden impuestos, transporte, seguro, descuentos ni total final;
- `quote=null` produce estado de sección no disponible.

### Propuesta comercial

- tarjeta por artefacto reconocido `proposal`;
- metadatos secundarios: idioma, fecha, estado de revisión e ID abreviado;
- narrativa generada separada del snapshot comercial determinista;
- el posicionamiento se asocia por `product_id` al producto mostrado; una
  referencia no resoluble se conserva como texto con ID, sin inventar nombre;
- próximos pasos, preguntas abiertas y warnings usan listas semánticas;
- la tarjeta mantiene visible “Borrador — requiere revisión humana”;
- no ofrece aprobar, editar, regenerar, descargar ni enviar.

### Correo generado

- tarjeta por artefacto reconocido `email_draft`;
- asunto separado del cuerpo;
- cuerpo compuesto en el orden: introducción, resumen, preguntas, siguiente
  paso y cierre;
- bloque comercial determinista visualmente separado;
- destinatario ausente se muestra como pendiente, no se adivina desde texto;
- el contenido se etiqueta “Borrador de correo — no enviado”;
- no se crea enlace `mailto:` ni botón de envío.

### Cliente, oportunidad, seguimiento y memoria demo

- el cliente muestra `company_name`, `country_code` y `preferred_language`
  únicamente cuando llegan en `customer`;
- `customer=null` se presenta como “No se vinculó un cliente a esta ejecución”;
- la UI no reconstruye el cliente desde análisis, oportunidad, correo o memoria;
- oportunidad y seguimiento se presentan como registros internos simulados;
- no se afirma sincronización con CRM o calendario externos;
- stage, priority, score, mercado, volumen, fecha objetivo y resumen se muestran
  solo si llegan en el contrato;
- la memoria se ordena exactamente como llega y muestra categoría, contenido,
  confianza, fecha y procedencia;
- `source_inquiry_id` igual a la inquiry actual se etiqueta “Consulta actual”;
- otro `source_inquiry_id` se etiqueta “Interacción anterior”;
- `source_inquiry_id=null` se etiqueta “Procedencia no disponible”;
- la UI no clasifica hechos como actuales o previos por fecha ni por texto.

## Estados del resultado

Los estados siguientes pertenecen a la región de resultado, no sustituyen el
estado del run de Bloque 3.

| Estado UI | Condición | Tratamiento |
|---|---|---|
| `loading` | Run terminal y GET en curso, sin snapshot de resultado | Skeleton o texto anunciable; sin datos ficticios |
| `success` | Resultado válido con `status=completed` | Secciones disponibles; borradores siguen requiriendo revisión |
| `needs_review` | Resultado válido con `status=needs_review` | Banner de revisión humana y secciones parciales disponibles |
| `failed` | Resultado válido con `status=failed` | “Resultado comercial parcial”; B3 conserva error y retry |
| `unavailable` | GET falla o envelope superior es incompatible | Mensaje seguro y acción para repetir solo el GET |

### Transiciones

```text
waiting_terminal -> loading -> success
                           -> needs_review
                           -> failed
                           -> unavailable -> loading
```

- mientras el run esté `queued` o `running`, no se llama al endpoint y la
  región puede mostrar “Disponible al finalizar” sin skeleton infinito;
- al observar por primera vez un detalle terminal, se inicia un solo GET;
- no se espera a que la timeline termine de renderizar y no se modifica su
  cursor;
- cambiar de `runId` o desmontar cancela la lectura anterior;
- no hay polling de resultado;
- “Volver a intentar resultado” repite solo el GET y no crea ni reintenta runs;
- si ya existe un resultado válido y una relectura manual falla, se conserva el
  snapshot anterior y se muestra estado degradado no destructivo;
- `agent_run_id` o `status` inconsistentes con el detalle producen
  `unavailable` por contrato; no se corrigen en frontend.

### Parcialidad por sección

Una sección tiene uno de estos estados locales:

- `available`: forma reconocida y render seguro;
- `empty`: colección válida sin elementos;
- `missing`: valor `null` o artefacto esperado ausente;
- `incompatible`: forma, tipo o versión no reconocidos.

`missing` e `incompatible` muestran un mensaje específico dentro de la sección.
No convierten por sí solos el resultado superior en `unavailable`. Las demás
secciones continúan visibles y operativas.

## Acciones de copiar

### Controles permitidos

- “Copiar propuesta” en cada propuesta reconocida;
- “Copiar asunto” en cada correo reconocido;
- “Copiar correo” en cada correo reconocido.

### Reglas vinculantes

- usar `navigator.clipboard.writeText` desde una acción explícita;
- copiar texto plano compuesto a partir de campos ya validados y visibles;
- no copiar JSON, HTML, IDs ocultos, metadata interna ni campos incompatibles;
- la propuesta copiada inicia con
  “BORRADOR — REQUIERE REVISIÓN HUMANA” y conserva labels de procedencia;
- el correo copiado inicia con “BORRADOR — NO ENVIADO”;
- “Copiar correo” no incluye el asunto, porque posee control separado;
- el orden copiado coincide con el orden visual;
- el contenido determinista no se mezcla con narrativa sin su encabezado;
- feedback de éxito “Copiado” y error “No se pudo copiar” se anuncia mediante
  una región `aria-live="polite"`;
- el feedback no depende solo de icono o color y vuelve al label original;
- fallo de clipboard no modifica ni selecciona automáticamente el contenido;
- no se conserva telemetría ni historial del texto copiado.

No se ofrece copiar el mensaje original, IDs, memoria ni registros demo en P0.

## Datos faltantes, degradados e incompatibles

- usar “No disponible en este resultado” para valores contractualmente
  ausentes;
- usar “No se generó en esta ejecución” para propuesta o correo ausentes;
- usar “Formato no compatible con esta versión” cuando falle un guard;
- usar “Dato pendiente” para faltantes comerciales informados por backend;
- no usar guiones ambiguos para `null` sin label accesible;
- no sustituir un email, nombre, país, precio, stock o fecha por datos de otra
  sección;
- no combinar el snapshot del artefacto con un quote diferente para ocultar
  discrepancias;
- no descartar warnings por duplicación aparente ni reinterpretarlos;
- conservar saltos de línea, caracteres internacionales y texto largo con
  `overflow-wrap` sin truncamiento silencioso;
- un error de una acción de copiar no degrada el resultado ni otras tarjetas.

## Seguridad de renderizado

- todo texto se renderiza como nodos React escapados;
- queda prohibido `dangerouslySetInnerHTML`;
- no se incorpora parser de markdown, HTML, iframe ni script;
- no se interpolan valores del resultado en estilos, atributos de evento,
  URLs externas o nombres de clase dinámicos no allowlisted;
- IDs solo forman enlaces internos cuando han pasado validación UUID y la ruta
  pertenece al producto;
- contenido desconocido nunca se enumera de forma genérica ni se imprime como
  JSON;
- los guards verifican tipo, presencia, literales, versión y arrays antes de
  construir view models;
- números no finitos, fechas inválidas o strings donde se esperan números
  convierten solo la sección afectada en incompatible;
- React keys usan IDs validados o índices locales sin exponer contenido;
- tablas y bloques de texto usan límites de layout, no de contenido copiado;
- mensajes de `ApiError` y correlation ID se tratan como texto, sin detalles ni
  body crudo;
- ninguna variable server-only, dirección interna o secreto aparece en la UI,
  clipboard o logs del navegador.

## Responsive y accesibilidad

- la región usa un `h2` “Resultado comercial”; no introduce otro `h1`;
- cada sección usa headings en orden y `aria-labelledby` cuando proceda;
- estados `loading` y feedback de copia usan anuncios discretos;
- warnings y errores usan texto e icono/label, nunca solo color;
- tablas conservan headers asociados y caption visible o accesible;
- el scroll horizontal de tabla es alcanzable con teclado y anunciado;
- datos label/valor usan `dl`, `dt` y `dd` cuando no requieren tabla;
- listas de faltantes, warnings, pasos y preguntas usan `ul`;
- botones poseen foco visible, nombre accesible y estado `disabled` real;
- ningún control es solo icono;
- el foco no salta al cargar el resultado ni después de copiar;
- targets interactivos mantienen al menos 44 por 44 CSS px;
- desde 360 px no hay overflow horizontal de página, superposición ni texto
  cortado; solo las tablas pueden desplazarse dentro de su contenedor;
- zoom al 200 % conserva lectura y controles;
- importes no dependen de alineación visual para asociarse a una línea;
- idiomas y códigos desconocidos conservan un fallback textual seguro;
- animaciones, si existen, respetan `prefers-reduced-motion`.

## Criterios de aceptación verificables

| ID | Criterio |
|---|---|
| B4-AC-01 | `api.getResult` no se llama para `queued` o `running`. |
| B4-AC-02 | Un run terminal muestra `loading` sin datos ficticios. |
| B4-AC-03 | Solo existe una lectura de resultado en curso por workspace y se cancela al cambiar de run. |
| B4-AC-04 | `completed`, `needs_review` y `failed` producen tratamientos textuales distintos. |
| B4-AC-05 | Un error de resultado produce `unavailable` y repetir ejecuta solo GET. |
| B4-AC-06 | Un snapshot válido se conserva si una relectura posterior falla. |
| B4-AC-07 | `agent_run_id` y `status` inconsistentes se rechazan como error de contrato. |
| B4-AC-08 | El mensaje original se renderiza como texto, preserva saltos y no ejecuta HTML. |
| B4-AC-09 | El análisis `1.0` se presenta con procedencia IA y sin inferir campos ausentes. |
| B4-AC-10 | Los faltantes provienen exactamente de `inquiry.missing_fields`. |
| B4-AC-11 | Un código de faltante futuro no rompe la sección y conserva su código. |
| B4-AC-12 | La recomendación `1.0` muestra productos, rationale, cantidades y certificaciones. |
| B4-AC-13 | `sellable_bottles` se muestra como stock observado y nunca como reservado. |
| B4-AC-14 | Datos de catálogo/stock se distinguen de resumen y rationale generados. |
| B4-AC-15 | La cotización muestra todas las líneas y los valores recibidos, sin recalcularlos. |
| B4-AC-16 | Céntimos EUR se formatean correctamente y `0` no se trata como ausente. |
| B4-AC-17 | Los siete supuestos deterministas se muestran junto al subtotal. |
| B4-AC-18 | La cotización se identifica como demo, no oferta final. |
| B4-AC-19 | Una propuesta `1.0` separa narrativa IA de snapshot determinista. |
| B4-AC-20 | Un correo `1.0` separa asunto, cuerpo y bloque comercial determinista. |
| B4-AC-21 | Propuesta y correo conservan labels de borrador aun con run `completed`. |
| B4-AC-22 | Artefactos desconocidos o inconsistentes no renderizan JSON y no rompen otros artefactos. |
| B4-AC-23 | Varios artefactos reconocidos del mismo tipo se muestran sin selección silenciosa. |
| B4-AC-24 | Copiar propuesta produce solo texto visible y comienza con el aviso obligatorio. |
| B4-AC-25 | Copiar asunto y correo son acciones separadas; el correo no incluye el asunto. |
| B4-AC-26 | Éxito y fallo de clipboard son accesibles y no alteran el contenido. |
| B4-AC-27 | Cliente, oportunidad y seguimiento se identifican como registros demo, usan fallbacks explícitos y no prometen integraciones. |
| B4-AC-28 | Memoria distingue consulta actual, interacción anterior y procedencia no disponible usando `source_inquiry_id`. |
| B4-AC-29 | Cada sección ausente o incompatible falla de forma aislada. |
| B4-AC-30 | `needs_review` se presenta como resultado útil pendiente de revisión, no como fallo. |
| B4-AC-31 | `failed` conserva secciones parciales y no duplica error ni retry de Bloque 3. |
| B4-AC-32 | La UI no contiene controles de envío, aprobación, edición, regeneración, reserva, sincronización, PDF o exportación. |
| B4-AC-33 | No se usa HTML/markdown crudo, `dangerouslySetInnerHTML` ni URLs externas derivadas del resultado. |
| B4-AC-34 | La región es navegable por teclado, tiene foco visible y anuncios no intrusivos. |
| B4-AC-35 | A 360 px y 200 % de zoom no hay overflow de página ni contenido inaccesible. |
| B4-AC-36 | Todas las llamadas del navegador permanecen bajo el proxy same-origin. |
| B4-AC-37 | Tipos estrictos, lint, tests y build frontend permanecen aprobados. |
| B4-AC-38 | El diff de implementación no modifica backend, dependencias ni contratos HTTP. |
| B4-AC-39 | Warnings globales y locales permanecen visibles, conservan su significado y no cambian por sí solos el estado del run. |

## Matriz criterio → prueba o evidencia

| Criterio | Prueba o evidencia futura obligatoria |
|---|---|
| B4-AC-01 | Integración del coordinador: estados activos no invocan `getResult` |
| B4-AC-02 | Componente: estado loading anunciable sin valores del fixture |
| B4-AC-03 | Integración del coordinador: guardia, abort y cambio de `runId` |
| B4-AC-04 | Componente parametrizado para los tres estados terminales |
| B4-AC-05 | Integración: `ApiError`, estado unavailable y reintento GET único |
| B4-AC-06 | Integración: snapshot previo más fallo posterior |
| B4-AC-07 | Unitario del adapter: IDs y estados discrepantes |
| B4-AC-08 | Componente con payload de HTML/script tratado como texto |
| B4-AC-09 | Unitario del guard de análisis y componente de procedencia |
| B4-AC-10 | Unitario: la lista visible coincide con el fixture backend |
| B4-AC-11 | Componente: código futuro con fallback estable |
| B4-AC-12 | Unitario del guard y componente de recomendación completa |
| B4-AC-13 | Componente: stock observado, ausencia de lenguaje de reserva |
| B4-AC-14 | Componente más evidencia visual de labels de procedencia |
| B4-AC-15 | Componente con valores deliberadamente no recalculables |
| B4-AC-16 | Unitarios de formato para cero, céntimos y EUR |
| B4-AC-17 | Componente: siete supuestos visibles |
| B4-AC-18 | Componente: label comercial vinculante |
| B4-AC-19 | Guard de propuesta y componente con dos procedencias |
| B4-AC-20 | Guard de email y componente con asunto/cuerpo/bloque comercial |
| B4-AC-21 | Componente con `completed` y artefactos `needs_review` |
| B4-AC-22 | Unitario con tipo, versión y forma desconocidos; ausencia de JSON |
| B4-AC-23 | Componente con dos propuestas y dos emails |
| B4-AC-24 | Unitario del compositor de clipboard de propuesta |
| B4-AC-25 | Unitarios de compositores de asunto y cuerpo |
| B4-AC-26 | Integración con clipboard resuelto y rechazado más revisión teclado |
| B4-AC-27 | Componente con cliente presente/nulo, oportunidad y seguimiento; revisión de promesas visuales |
| B4-AC-28 | Componente con los tres valores de `source_inquiry_id` |
| B4-AC-29 | Matriz de fixtures parciales por sección |
| B4-AC-30 | Componente y evidencia visual de `needs_review` |
| B4-AC-31 | Componente con resultado parcial; revisión de no duplicación B3 |
| B4-AC-32 | Búsqueda de controles prohibidos y revisión manual |
| B4-AC-33 | Test de payload hostil y búsqueda de APIs de render prohibidas |
| B4-AC-34 | Revisión manual completa con teclado y foco visible |
| B4-AC-35 | Capturas y checklist manual a 360 px y 200 % de zoom |
| B4-AC-36 | Tests de cliente/proxy e inspección de requests del navegador |
| B4-AC-37 | `make check-web` |
| B4-AC-38 | `git diff --check` y revisión de paths del PR |
| B4-AC-39 | Componente con warnings globales/locales, listas vacías y estado del run inalterado |

## Estrategia de pruebas de implementación

### Unitarias

- guards de análisis, recomendación, propuesta, email y supuestos;
- adapter superior y estados de sección;
- formatos de moneda, fecha, idioma, país y fallback;
- labels de faltantes y procedencia de memoria;
- compositores de texto plano para clipboard;
- rechazo de NaN, fechas inválidas, versión futura y arrays mal formados.

### Componentes

- cinco estados visibles del resultado;
- todas las secciones completas;
- cada sección nula, vacía e incompatible;
- warnings globales y locales;
- múltiples artefactos del mismo tipo;
- payloads con HTML, URLs y strings largos;
- labels de procedencia y promesas demo.

### Integración frontend

- coordinación entre estado terminal de B3 y una lectura de resultado;
- abort al desmontar o cambiar run;
- error inicial, retry GET y fallo degradado posterior;
- clipboard disponible, rechazado y ausente;
- same-origin y error envelope.

### Evidencia manual

- escritorio y 360 px;
- zoom 200 %;
- teclado, foco y lector de pantalla básico;
- contraste y estados sin color;
- copy/paste en un editor de texto para confirmar contenido plano;
- revisión de que no hay acción visual fuera de alcance.

El E2E con backend real y fake Qwen permanece en Bloque 5. Bloque 4 sí debe
usar fixtures que reproduzcan exactamente el contrato backend vigente, no
formas inventadas para la UI.

## Archivos previstos para la futura implementación

| Archivo | Cambio previsto |
|---|---|
| `apps/web/src/components/run-workspace.tsx` | Integrar la región de resultado sin alterar timeline o retry |
| `apps/web/src/components/commercial-result.tsx` | Presentar estados y composición principal |
| `apps/web/src/components/commercial-artifacts.tsx` | Presentar propuesta, correo y copiar contenido |
| `apps/web/src/lib/commercial-result.ts` | Guards, adapters, formatos, procedencia y texto de clipboard |
| `apps/web/src/lib/api/types.ts` | Añadir view-facing types cerrados sin cambiar el envelope HTTP |
| `apps/web/src/lib/api/client.ts` | Aceptar `AbortSignal` opcional en `getResult` |
| `apps/web/src/app/globals.css` | Estilos responsive, procedencia, tablas, estados y foco |
| `apps/web/tests/commercial-result.test.ts` | Guards, adapters, formatos y clipboard |
| `apps/web/tests/commercial-result.test.tsx` | Estados, secciones, seguridad y accesibilidad estructural |
| `apps/web/tests/run-workspace.test.tsx` | Integración con terminales sin regresión de Bloque 3 |
| `apps/web/tests/client.test.ts` | GET de resultado, same-origin, signal y errores |

Los nombres de componentes pueden ajustarse antes de implementar para respetar
la estructura real, pero no se crearán archivos backend. Si la implementación
descubre que un criterio requiere modificar `apps/api`, debe detenerse y
actualizar esta documentación para aprobación previa.

## Riesgos y mitigaciones

| Riesgo | Nivel | Mitigación |
|---|---:|---|
| JSON opaco rompe tipado o render | Alto | Guards versionados y view models cerrados |
| Texto IA parece dato confirmado | Alto | Procedencia textual por bloque y copy con avisos |
| Quote se interpreta como oferta final | Alto | Supuestos visibles y label de cotización demo |
| Stock observado parece reservado | Alto | Lenguaje vinculante y prohibición de promesa |
| Parcialidad oculta información útil | Alto | Estado independiente por sección |
| B4 duplica B3 | Medio | Región separada; error y retry permanecen en B3 |
| Payload hostil introduce XSS | Alto | React text, sin HTML/markdown ni URLs derivadas |
| Copiar pierde contexto de revisión | Alto | Prefijos obligatorios y labels de procedencia |
| Tablas rompen móvil | Medio | Una columna y scroll contenido accesible |
| Artefacto futuro se interpreta mal | Medio | Fail closed por tipo y schema version |
| UI introduce reglas comerciales | Alto | Solo formato; sin recálculo ni inferencias |
| Alcance crece hacia editor/CRM/PDF | Alto | Controles prohibidos y revisión de paths/promesas |

## Bloqueos y regla de detención

No existe una brecha backend imprescindible en la baseline inspeccionada.
`RunResult` ya contiene el conjunto necesario para el Bloque 4 y la
recomendación contiene la evidencia de stock.

La implementación debe detenerse antes de modificar backend si aparece alguno
de estos bloqueos:

- UC-001 no expone una sección que esta especificación considera obligatoria;
- el schema real deja de distinguir quote determinista de narrativa;
- no puede identificarse con seguridad proposal o email draft por tipo y
  versión;
- la única solución propuesta requiere un nuevo endpoint, campo, mutación o
  integración;
- un criterio exige recalcular o inferir una regla comercial en navegador.

En ese caso se documentará la brecha con evidencia, impacto, alternativas y
recomendación, y se solicitará aprobación antes de tocar `apps/api`.

## Definition of Done del Bloque 4

### Documental

- esta especificación está aprobada y fusionada antes de programar;
- contrato, brecha frontend, estados, seguridad y procedencia están definidos;
- cada criterio B4-AC tiene prueba o evidencia asignada;
- riesgos, exclusiones, bloqueos y archivos previstos están registrados;
- no se crea ADR sin decisión arquitectónica significativa.

### Funcional de la futura implementación

- el resultado terminal se obtiene del backend real mediante same-origin;
- `loading`, `success`, `needs_review`, `failed` y `unavailable` son explícitos;
- recomendación, stock, quote, propuesta y correo se comprenden sin JSON;
- datos deterministas y texto IA no se confunden;
- secciones parciales no derriban el workspace;
- copiar funciona como texto plano con avisos de revisión;
- no existen controles o promesas fuera de alcance;
- B3 conserva intactos observabilidad y retry.

### Técnica de la futura implementación

- TypeScript estricto, lint, tests y build aprobados;
- guards y adapters cubren payload completo, parcial, futuro y hostil;
- requests se cancelan y no se solapan;
- no se añade dependencia runtime;
- no se modifica backend, contrato HTTP, Compose ni CI salvo aprobación
  documental posterior;
- `git diff --check` aprobado.

### UX y accesibilidad de la futura implementación

- experiencia funcional desde 360 px y con zoom 200 %;
- navegación completa por teclado y foco visible;
- headings, tablas, listas y estados usan semántica apropiada;
- estados y procedencia no dependen solo de color;
- feedback de clipboard es anunciable y no roba foco;
- payloads largos o internacionales no rompen el layout.

## No se considera terminado

- renderizar `JsonObject` mediante casts sin validación;
- imprimir JSON o markdown como interfaz;
- mostrar propuesta o email sin label de borrador;
- ocultar supuestos de quote o prometer stock reservado;
- seleccionar silenciosamente un artefacto entre varios;
- derribar todo el resultado por una sección incompatible;
- duplicar error, retry, timeline o tools del Bloque 3;
- agregar botón de enviar, aprobar, editar, regenerar, PDF o sincronizar;
- aprobar visualmente sin tests de contrato parcial y payload hostil;
- declarar Bloque 4 cerrado sin evidencia B4-AC-01 a B4-AC-39.
