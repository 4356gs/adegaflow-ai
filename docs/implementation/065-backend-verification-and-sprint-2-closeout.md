# Sprint 2 Bloque 9 — Verificación backend y cierre

- **Estado:** Ready for review
- **Sprint:** 2 — Núcleo funcional
- **Bloque:** 9
- **Baseline:** `f65ba23580c003059b4667a678733d0071d50516`
- **Rama documental:** `docs/sprint2-block9-plan`
- **Rama de implementación prevista:** `test/sprint2-backend-closeout`
- **Fecha:** 2026-07-18
- **ADRs vinculantes:** ADR-011 y ADR-014
- **Documentos relacionados:** `052-implementation-plan.md`,
  `054-test-strategy.md`, `055-acceptance-scenarios.md`,
  `056-sprint-2-definition-of-done.md` y
  `064-api-and-async-execution.md`

## Objetivo

Cerrar Sprint 2 con evidencia reproducible de que UC-001 funciona de extremo a
extremo en el backend, desde el comando HTTP que crea una inquiry hasta la
lectura del resultado comercial, la oportunidad, el seguimiento y la memoria.

El bloque añade pruebas y soporte de demostración, corrige únicamente defectos
necesarios para satisfacer contratos ya aprobados y actualiza la documentación
de cierre. No añade capacidades de producto ni cambia el contrato API salvo que
se descubra una divergencia inequívoca respecto de los documentos vinculantes;
un cambio material de contrato exige detener el bloque y volver a revisión.

## Regla de inicio

Este documento define el alcance y el orden vinculante. Mientras su PR
documental no esté revisada, aprobada y fusionada:

- no se crean pruebas nuevas del Bloque 9;
- no se crean scripts ni targets de demostración;
- no se modifica código de producto;
- no se declara cerrado Sprint 2;
- no se inicia Sprint 3.

Después del merge se crea la rama de implementación desde el nuevo `main`. La
implementación debe seguir el orden definido al final de este documento.

## Alcance incluido

- inventario de cobertura existente y brechas contra AT-001 a AT-020;
- pruebas unitarias adicionales solo para brechas de reglas críticas;
- pruebas de contrato HTTP y OpenAPI;
- integración con SQLite real temporal y Qwen mock completo;
- end-to-end backend determinista a través de HTTP y del dispatcher;
- verificación de idempotencia HTTP e idempotencia de acciones internas;
- verificación de polling de estado y eventos;
- verificación del resultado expandido desde tablas autoritativas;
- verificación de retry mediante un run nuevo e inmutable;
- verificación de segunda sesión y recuperación de memoria;
- smoke test live Qwen opcional y aislado;
- demostración reproducible desde terminal;
- recorrido equivalente desde Swagger cuando exista configuración live;
- migraciones y seeds sobre una base desechable;
- build y ejecución Docker con un solo worker;
- calidad, cobertura, documentación y evidencia de cierre.

## Fuera de alcance

- frontend o cualquier trabajo de Sprint 3;
- nuevas capacidades comerciales;
- aprobación, rechazo o edición de artefactos;
- envío de correo real;
- CRM o calendario externos;
- reserva, decremento o cualquier cambio de inventario;
- WebSockets, SSE o long polling;
- Redis, Celery, RabbitMQ o cola durable;
- múltiples workers, procesos o instancias API;
- PostgreSQL;
- autenticación, autorización o multitenencia;
- despliegue final;
- materiales finales o submission del hackathon;
- endpoints para resetear datos de demo;
- cambios de modelo, prompts o reglas comerciales para mejorar una demo;
- pruebas de carga, alta disponibilidad o recuperación distribuida.

## Principios de verificación

1. Las reglas deterministas se prueban sin red.
2. El camino de cierre obligatorio usa Qwen mock y datos ficticios.
3. La prueba end-to-end entra por HTTP; no llama directamente al orquestador.
4. El mock sustituye solo el límite del proveedor. FastAPI, dispatcher,
   servicios, tools, repositorios, SQLite y read models son reales.
5. No se hardcodea el resultado terminal en el endpoint ni en el orquestador.
6. Cada espera tiene deadline corto y mensaje de fallo; no se usan sleeps
   abiertos ni tests dependientes del orden.
7. Cada test crea su base temporal y controla su reloj cuando el tiempo sea
   parte del resultado.
8. Los tests live permanecen fuera de la suite por defecto.
9. Una captura visual no sustituye una aserción automatizada.
10. El warning conocido de Starlette TestClient se registra como no bloqueante
    mientras no oculte warnings nuevos ni fallos.

## Prioridades

- **P0:** bloquea el cierre; cubre el camino feliz, seguridad transaccional,
  contratos públicos, idempotencia, retry, resultado y operación de un worker.
- **P1:** debe quedar verde para el cierre, pero una desviación puede aceptarse
  únicamente con causa, riesgo, owner y fecha de corrección documentados.
- **Live opcional:** aporta confianza sobre el proveedor, pero no puede bloquear
  CI ni sustituir una prueba determinista.

## Matriz vinculante de pruebas

| ID | Nivel | Prioridad | Verificación | Aceptación relacionada |
|---|---|---:|---|---|
| B9-U01 | Unitaria | P0 | fingerprints y receipts iguales reutilizan acciones; contenido distinto produce conflicto | AT-008, AT-013 |
| B9-U02 | Unitaria | P0 | política cerrada de retry acepta errores transitorios y rechaza éxito, human review y errores definitivos | AT-007, AT-018 |
| B9-U03 | Unitaria | P0 | resultado expandido usa quote, artefactos y acciones de tablas autoritativas | AT-019 |
| B9-U04 | Unitaria | P1 | payloads públicos filtran secretos, raw responses y PII no necesaria | AT-012, AT-019 |
| B9-U05 | Unitaria | P1 | cálculo de polling terminal y cursores no crea huecos ni duplicados | AT-015 |
| B9-C01 | Contrato | P0 | OpenAPI publica `/health` y producto solo bajo `/api/v1` | AT-020 |
| B9-C02 | Contrato | P0 | POST de inquiry, run y retry documentan `Idempotency-Key`, success y errores | AT-015, AT-016, AT-018 |
| B9-C03 | Contrato | P0 | schemas rechazan extras, UUID inválidos y límites fuera de rango | AT-016, AT-019 |
| B9-C04 | Contrato | P0 | errores usan envelope seguro con correlation ID y sin stack trace | AT-005, AT-007, AT-012 |
| B9-C05 | Contrato | P0 | resultado terminal contiene secciones opcionales tipadas y el no terminal devuelve `RUN_NOT_TERMINAL` | AT-014, AT-019 |
| B9-I01 | Integración | P0 | `FakeQwenClient` completa análisis, tools, recomendación, propuesta y correo | AT-001, AT-013 |
| B9-I02 | Integración | P0 | dispatcher persiste `queued` antes de enqueue, usa una sesión por run y un consumidor | AT-015 |
| B9-I03 | Integración | P0 | misma key y fingerprint no duplica inquiry, run, enqueue ni acciones; fingerprint distinto entra en conflicto | AT-008, AT-016 |
| B9-I04 | Integración | P0 | fallo entre oportunidad, seguimiento y memoria revierte la unidad completa y conserva quote/artefactos | AT-010, AT-014 |
| B9-I05 | Integración | P0 | interrupción produce `RUN_INTERRUPTED`; retry crea otro run y deja el original inmutable | AT-017, AT-018 |
| B9-I06 | Integración | P0 | eventos se leen en orden mediante `after_sequence` hasta estado terminal | AT-015 |
| B9-I07 | Integración | P0 | oportunidad, seguimiento y memoria leídos por API pertenecen a la misma inquiry/run | AT-013, AT-019 |
| B9-I08 | Integración | P1 | segundo run del mismo comprador recupera solo memoria activa | AT-009 |
| B9-I09 | Integración | P1 | JSON inválido se repara una vez y luego falla de forma segura | AT-005 |
| B9-I10 | Integración | P1 | tool inexistente y límites de rondas/tools nunca ejecutan código fuera de allowlist | AT-006, AT-011 |
| B9-I11 | Integración | P1 | stock insuficiente no produce una cotización falsa | AT-003 |
| B9-I12 | Integración | P1 | comprador desconocido se crea solo con identidad mínima suficiente | AT-004 |
| B9-I13 | Integración | P1 | datos faltantes quedan visibles y no se inventan | AT-002 |
| B9-E01 | E2E backend | P0 | flujo HTTP completo con Qwen mock termina `needs_review` y expone resultado comercial | AT-001, AT-013, AT-015, AT-019 |
| B9-E02 | E2E backend | P0 | repetir los tres POST con keys equivalentes devuelve los mismos recursos sin reencolar | AT-016 |
| B9-E03 | E2E backend | P0 | reejecutar las acciones del mismo run conserva exactamente una oportunidad, un seguimiento y las memorias deduplicadas | AT-008, AT-013 |
| B9-E04 | E2E backend | P0 | timeout simulado produce fallo retryable; el retry crea un nuevo run que completa | AT-007, AT-018 |
| B9-E05 | E2E backend | P1 | segunda inquiry del comprador usa la memoria creada por la primera | AT-009 |
| B9-D01 | Docker | P0 | imagen construye, migra, siembra, inicia saludable y su comando efectivo contiene `--workers 1` | DoD de ingeniería |
| B9-L01 | Live Qwen | Opcional | smoke de texto/JSON/tool calling con datos ficticios y sin persistir secretos | AT-012, ADR-011 |

Las pruebas existentes se reutilizan cuando ya demuestran exactamente una fila
de la matriz. No se duplican por cambiarles el nombre. La implementación debe
añadir una tabla de trazabilidad en el documento de cierre que relacione cada
ID B9 con el archivo y nombre real del test que la satisface.

## Integración completa con Qwen mock

### Límite del mock

El mock implementa el mismo protocolo neutral consumido por los servicios. No
simula FastAPI, SQLAlchemy, el dispatcher, las tools ni los read models.

Debe soportar una secuencia inspeccionable para:

1. análisis estructurado de la inquiry;
2. solicitud de recuperación de memoria;
3. búsqueda de catálogo;
4. consulta de detalle de producto;
5. consulta de stock;
6. recomendación estructurada;
7. propuesta narrativa;
8. borrador de correo.

La prueba verifica tanto las salidas como el orden y los límites de llamadas.
Las respuestas mock contienen únicamente datos ficticios coherentes con el
seed; los precios, stock, totales, score, prioridad y fecha de seguimiento se
siguen calculando o validando de forma determinista fuera del modelo.

### Escenario feliz obligatorio

- comprador: Rhein Selection GmbH;
- mercado: Alemania;
- idioma: inglés;
- volumen: 600 botellas;
- dos referencias activas y con stock suficiente;
- quote en EUR y céntimos enteros;
- propuesta y correo en `needs_review`;
- una oportunidad;
- un seguimiento a siete días desde el reloj inyectado;
- memoria explícita, normalizada y activa.

El test obtiene los IDs desde las respuestas; no depende de IDs generados
previamente salvo los identificadores canónicos del seed.

### Escenario de retry obligatorio

El mock/script provoca un timeout tipado en el primer run. Se comprueba:

- estado terminal `failed` y código público seguro;
- `retryable=true`;
- ausencia de acciones comerciales parciales incompatibles;
- POST de retry con una key nueva responde `202`;
- el nuevo ID difiere del original y conserva `retry_of_run_id`;
- el original no cambia;
- repetir la key de retry devuelve el mismo segundo run sin reencolar;
- el segundo run completa usando la secuencia mock restante.

## Política del test live opcional

### Propósito

Detectar cambios de compatibilidad en el endpoint OpenAI-compatible de Qwen.
No valida reglas de negocio y no es parte de la suite determinista de cierre.

### Prerrequisitos

- `DASHSCOPE_API_KEY` disponible solo como variable de entorno local;
- endpoint y modelo conformes con ADR-011;
- conectividad explícita a Qwen Cloud;
- cuota disponible y autorización consciente para consumirla;
- datos exclusivamente ficticios;
- ejecución desde una base desechable cuando exista persistencia;
- marker `live_qwen` seleccionado de forma explícita;
- ningún secreto impreso, persistido, grabado o añadido a Git.

### Política de ejecución

- CI y `make check-api` lo excluyen;
- no se ejecuta automáticamente al iniciar la API ni la demo;
- timeout y número de reintentos permanecen acotados;
- un fallo se registra como evidencia diagnóstica, no como fallo del Sprint 2;
- si se ejecuta, se documentan fecha, modelo efectivo, casos y resultado, nunca
  la clave ni payloads sensibles;
- el spike S-01 a S-04 ya aprobado conserva el gate live obligatorio.

El comando objetivo después de implementar el bloque será:

```bash
pytest apps/api/tests -m live_qwen -q
```

## Demostración backend

### Camino autoritativo: terminal con Qwen mock

La implementación añadirá un runner de demostración aislado que use una base
temporal, cargue el seed canónico, levante la aplicación en proceso con
lifespan real e inyecte Qwen mock. No añadirá endpoints de demo ni cambiará la
configuración de producción.

Comando objetivo:

```bash
make demo-backend
```

El runner debe imprimir, en orden y con JSON legible:

1. migración y carga idempotente del seed temporal;
2. `POST /api/v1/inquiries` y su repetición equivalente;
3. `POST /api/v1/inquiries/{id}/agent-runs` con respuesta `202`;
4. polling de run y eventos hasta estado terminal;
5. `GET /api/v1/agent-runs/{id}/result`;
6. `GET /api/v1/opportunities/{id}`;
7. `GET /api/v1/customers/{id}/memory`;
8. conteos que prueban una oportunidad, un seguimiento y memoria deduplicada;
9. segunda inquiry del mismo comprador con memoria recuperada.

El retry se demuestra por separado para mantener legible la evidencia:

```bash
make demo-backend-retry
```

Este segundo escenario muestra timeout simulado, run original inmutable, POST
de retry `202`, `retry_of_run_id`, polling y finalización del nuevo run.

Ambos comandos deben devolver código cero solo si todas las comprobaciones se
cumplen. No usan la red ni `DASHSCOPE_API_KEY`.

### Camino opcional: Swagger con Qwen live

Con la API iniciada, la documentación interactiva está en:

```text
http://localhost:8000/docs
```

El recorrido manual usa las mismas rutas y keys del runner. Requiere Qwen
configurado y puede consumir cuota. Swagger no recibe un modo mock de
producción; por tanto, este recorrido es complementario y no constituye el
gate reproducible del bloque.

## Verificaciones específicas

### Idempotencia

Se separan dos límites:

- **HTTP:** misma key y mismo comando devuelve el mismo recurso; key reutilizada
  con otro fingerprint devuelve `IDEMPOTENCY_CONFLICT`; no hay segundo enqueue.
- **Negocio:** receipts iguales reutilizan oportunidad, seguimiento y memorias;
  fingerprint distinto no sobrescribe registros previos.

Las aserciones consultan conteos y relaciones en SQLite, no solo códigos HTTP.

### Polling

- el POST de run responde `202` con `queued` persistido;
- cada GET es idempotente;
- `after_sequence` avanza sin repetir ni omitir eventos;
- el polling termina solo en `needs_review`, `completed` o `failed`;
- existe un deadline total corto y determinista;
- no se usa WebSocket, SSE ni long polling.

### Resultado expandido

- antes del estado terminal devuelve 409 `RUN_NOT_TERMINAL`;
- al terminar devuelve las secciones disponibles;
- quote, artefactos, oportunidad, seguimiento y memoria provienen de sus tablas;
- una referencia falsa en `result_payload` no prevalece sobre datos
  autoritativos;
- no aparecen API keys, chain of thought ni respuesta cruda de Qwen.

### Retry

- solo códigos de la allowlist son retryable;
- siempre crea un run nuevo;
- el run original, sus eventos y resultados permanecen inmutables;
- no copia receipts ni resultados al nuevo intento;
- una key repetida no crea otro retry ni otro enqueue;
- un run en `needs_review` se rechaza como no retryable.

### No duplicación comercial

Después del camino feliz y de repetir comandos/acciones se verifica por
consulta directa y por API:

- exactamente una oportunidad para la inquiry;
- exactamente un seguimiento asociado a esa oportunidad;
- un receipt por cada acción interna;
- memorias normalizadas sin duplicados por contenido canónico;
- ninguna mutación de inventario.

## Migraciones y seeds reproducibles

Las verificaciones destructivas se ejecutan únicamente sobre una URL SQLite
temporal identificada de forma explícita. Nunca se usa `db-reset` contra una
base no demostrablemente desechable.

Secuencia mínima:

```bash
export DATABASE_URL=sqlite:////tmp/adegaflow-block9.db
rm -f /tmp/adegaflow-block9.db
make db-upgrade
make seed-demo
make seed-demo
make seed-demo-reset
```

La evidencia debe mostrar:

- Alembic alcanza un único head `0005_http_async_runs`;
- upgrade desde base funciona;
- downgrade a `0004` y upgrade a `0005` son reversibles;
- ejecutar seed dos veces no duplica filas;
- reset restaura los valores canónicos;
- la base temporal se identifica en el transcript.

La eliminación anterior se limita al archivo temporal literal mostrado. No se
permite un glob, variable no resuelta ni directorio amplio.

## Ejecución Docker con un solo worker

Comandos de verificación:

```bash
docker compose build api
docker compose run --rm api alembic -c alembic.ini upgrade head
docker compose run --rm api python -m app.db.seed
docker compose up -d api
docker compose ps api
docker compose exec api sh -c 'tr "\0" " " </proc/1/cmdline'
curl --fail http://localhost:8000/health
docker compose down
```

La prueba pasa solo si:

- el contenedor está healthy;
- el comando efectivo contiene `uvicorn` y `--workers 1`;
- existe un único proceso worker de aplicación;
- `ASYNC_RUN_QUEUE_CAPACITY` está dentro de 1 a 100;
- la base y el seed son accesibles dentro del contenedor;
- no se introduce un segundo consumidor ni una cola externa.

`docker compose down` no elimina el volumen. La opción `-v` queda fuera de los
comandos normales porque destruiría los datos persistidos del demo.

## Comandos de calidad y cobertura

Desde la raíz, con el entorno virtual activo:

```bash
make install-api
make check-api
pytest apps/api/tests -m "not live_qwen" --cov=app --cov-branch --cov-report=term-missing
git diff --check
```

Gates:

- Ruff sin errores;
- mypy strict sin errores;
- todas las pruebas no-live en verde;
- cobertura global de al menos 80 %, sin reducir cobertura de reglas críticas;
- reglas monetarias, stock, idempotencia y transacciones críticas cubiertas;
- ningún test depende de red, orden global o datos persistentes previos;
- ningún TODO crítico nuevo;
- warning conocido documentado y sin warnings inesperados ocultos.

## Evidencia de cierre requerida

La rama de implementación no está lista para PR hasta producir:

1. `docs/implementation/066-sprint-2-closure.md` con baseline, commit, fecha y
   resultado por AT-001 a AT-020;
2. tabla B9 → archivo/test real para toda la matriz vinculante;
3. transcript resumido de `make demo-backend` y
   `make demo-backend-retry`, sin secretos;
4. evidencia de respuesta `202`, polling, eventos y resultado expandido;
5. IDs que prueben que retry creó un run nuevo y conservó el original;
6. conteos antes/después que prueben no duplicación de oportunidad,
   seguimiento y memoria;
7. resultado de migraciones y seeds sobre base temporal;
8. evidencia Docker de health y `--workers 1`;
9. Ruff, mypy, pytest, cobertura y `git diff --check`;
10. OpenAPI verificado sin rutas de producto fuera de `/api/v1`;
11. actualización de `README.md`, `apps/api/README.md`, `VERIFICATION.md` y
    `CHANGELOG.md`;
12. resultado live opcional, si se ejecutó, claramente separado del gate;
13. riesgos residuales y exclusiones conservadas;
14. confirmación explícita de que no se implementó frontend ni Sprint 3.

No se requieren screenshots para cerrar este bloque. Se aceptan solo como apoyo
de la demo, nunca como sustituto de resultados automatizados y transcripts.

## Criterios de aceptación del Bloque 9

1. La matriz tiene un test real o una justificación aprobada por cada fila.
2. AT-001 a AT-020 están trazados y los escenarios P0 pasan.
3. El E2E entra por HTTP y completa el flujo con Qwen mock.
4. El POST de run devuelve `202` antes de completar el trabajo.
5. Estado y eventos se observan mediante polling acotado.
6. El resultado terminal incluye análisis, recomendación, quote, artefactos y
   acciones disponibles desde fuentes autoritativas.
7. Repetir POST equivalentes no duplica inquiry, run ni enqueue.
8. Repetir acciones del mismo run no duplica oportunidad, seguimiento ni
   memoria.
9. Un fallo recuperable crea mediante retry un run nuevo; el original queda
   inmutable.
10. La segunda sesión recupera memoria activa del comprador.
11. El stock permanece sin cambios durante todas las pruebas y demos.
12. La demo terminal funciona sin red ni secreto.
13. El test live permanece opcional, explícito y fuera de CI.
14. Migraciones y seeds son reproducibles en una base temporal.
15. Docker inicia saludable con exactamente un worker.
16. Ruff, mypy strict, tests y cobertura cumplen sus gates.
17. La documentación de cierre contiene evidencia verificable y no afirma
    capacidades excluidas.
18. No existe cambio material no aprobado del contrato API o arquitectura.

## Definition of Done del Bloque 9

- plan documental aprobado y fusionado antes de implementar;
- rama de implementación creada desde `main` actualizado;
- inventario de cobertura y brechas completado;
- matriz B9 satisfecha y trazada;
- Qwen mock completo cubre todas las fases del flujo;
- E2E feliz, idempotente, retry y segunda sesión en verde;
- no duplicación comercial demostrada con conteos;
- polling, resultado expandido y seguridad pública verificados;
- migraciones y seeds reproducibles;
- Docker verificado con un worker;
- comandos de demo deterministas y documentados;
- test live opcional aislado;
- `make check-api` en verde;
- cobertura objetivo alcanzada o desviación P1 formalmente aceptada;
- documentación de cierre y archivos de estado actualizados;
- PR de implementación revisada, CI aprobada y fusionada;
- `main` post-merge limpio y verificado;
- Sprint 2 declarado cerrado solo después de esa verificación.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| E2E falso por mock excesivo | sustituir solo el proveedor; usar stack real restante |
| test asíncrono intermitente | reloj controlado, deadlines y lifecycle real |
| demo modifica datos locales | base temporal y sin endpoint reset |
| retry duplica acciones | run nuevo, receipts, conteos e inmutabilidad explícita |
| read model oculta datos inconsistentes | comparar API con tablas autoritativas |
| live consume cuota o falla por red | manual, opcional y no bloqueante |
| Docker inicia más de un worker | inspeccionar comando y procesos efectivos |
| nueva prueba revela defecto de contrato | corregir solo divergencia aprobada; detener ante cambio material |
| documentación afirma más de lo probado | tabla de trazabilidad y evidencia por criterio |
| cierre se confunde con submission | mantener despliegue final y hackathon fuera del bloque |

## Exclusiones conservadas al cierre

Cerrar Sprint 2 no implica soporte para producción. Permanecen fuera:

- interfaz web;
- revisión humana ejecutable desde API;
- integraciones externas;
- entrega real de artefactos;
- concurrencia distribuida;
- durabilidad de cola;
- autenticación;
- PostgreSQL;
- despliegue final y submission.

Estas limitaciones deben aparecer en la demo y en el documento de cierre.

## Gate hacia Sprint 3

Sprint 3 solo puede comenzar cuando:

- la PR de implementación del Bloque 9 está fusionada;
- `main` pasa `make check-api` y la verificación Docker;
- los P0 y los AT exigidos por `056-sprint-2-definition-of-done.md` están en
  verde;
- el contrato OpenAPI no cambia de forma material y no publica aliases sin
  versión;
- la demo mock completa es reproducible desde cero;
- oportunidad, seguimiento y memoria no se duplican;
- el resultado y el retry son consumibles por un futuro frontend;
- la restricción de un worker sigue siendo suficiente para la demo;
- los riesgos P1 aceptados, si existen, tienen owner y fecha;
- `066-sprint-2-closure.md` declara Sprint 2 cerrado con evidencia.

Si cualquiera de estas condiciones falla, el siguiente trabajo pertenece aún
al Sprint 2. No se abre frontend para ocultar o compensar una brecha backend.

## Orden vinculante de implementación

1. crear rama desde `main` posterior al merge documental;
2. inventariar tests existentes y mapearlos a B9 y AT-001 a AT-020;
3. ejecutar baseline de calidad, cobertura, migración y seed sin modificar
   código;
4. añadir fixtures Qwen mock compartidas y secuencias de error;
5. cubrir brechas unitarias y de contrato P0;
6. cubrir integración P0 con SQLite temporal y dispatcher real;
7. implementar E2E feliz e idempotencia completa;
8. implementar E2E de retry e inmutabilidad;
9. implementar segunda sesión y casos P1 faltantes;
10. añadir runner y targets de demo sin endpoints nuevos;
11. verificar migraciones y seeds en base temporal;
12. verificar build y ejecución Docker con un worker;
13. ejecutar calidad y cobertura completas;
14. ejecutar live opcional solo si se cumplen sus prerrequisitos;
15. redactar `066-sprint-2-closure.md` y actualizar README, API README,
    VERIFICATION y CHANGELOG;
16. revisar diff, exclusiones, secretos, trazabilidad y evidencia;
17. abrir PR de implementación; no comenzar Sprint 3;
18. después del merge, verificar `main` limpio y declarar el cierre.

Los pasos 4 a 15 no comienzan hasta completar los anteriores que les sirven de
gate. Un defecto funcional puede corregirse dentro del bloque solo si restaura
un contrato ya aprobado; cualquier expansión o cambio material vuelve a
revisión documental.
