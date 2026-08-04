# Sprint 3 — Bloque 1: fundación web y contrato

## Estado

- **Estado:** Approved for implementation
- **Baseline:** `8ebf0b29be9e4aa81605d090c259c5a4823f724f`
- **Baseline documental:** PR #14
- **Rama:** `feat/sprint3-web-foundation`
- **Objetivo único:** crear una base Next.js reproducible, segura y probada que
  consuma el backend existente mediante un límite same-origin.

Este documento concreta el Bloque 1 definido en `068-sprint-3-implementation-plan.md`.
No autoriza trabajo de los Bloques 2–5.

## Resultado observable

Al terminar el bloque:

1. `apps/web` arranca localmente y en un contenedor;
2. `GET /` muestra un shell mínimo, responsive, accesible y marcado como demo;
3. `GET /api/health` adapta el health no versionado de FastAPI;
4. `/api/v1/*` reenvía los endpoints P0 sin trasladar reglas de negocio;
5. los contratos y el acceso HTTP están centralizados y tipados;
6. errores de transporte usan un envelope seguro y correlation ID;
7. eventos públicos de tools pueden incluir `payload.tool_name`;
8. argumentos, resultados completos, secretos y datos personales siguen filtrados;
9. Compose levanta `web` y `api`; la API conserva exactamente un worker.

## Alcance incluido

### Scaffold `apps/web`

- Next.js App Router;
- React;
- TypeScript estricto;
- Tailwind CSS;
- ESLint;
- npm y lockfile;
- Node.js 22;
- alias `@/*`;
- salida `standalone` para Docker.

### Shell mínimo

- layout raíz y metadata básica;
- idioma español;
- skip link y foco visible;
- cabecera y navegación mínima sin enlaces rotos;
- indicador visible de entorno demo;
- contenedor responsive desde 360 px;
- página raíz temporal que explica el estado del bloque;
- acceso visible a `/api/health`.

El shell comprueba composición, identidad y accesibilidad básica. No sustituye
el cockpit del Bloque 2.

### Proxy same-origin

Se implementan dos límites explícitos:

| Ruta web | Destino FastAPI |
|---|---|
| `GET /api/health` | `GET /health` |
| `GET|POST /api/v1/*` | mismo método y path bajo `/api/v1/*` |

El proxy:

- conserva query string;
- reenvía el cuerpo cuando el método lo admite;
- reenvía solo `Content-Type`, `Idempotency-Key` y `X-Correlation-ID`;
- conserva status y solo `Content-Type`, `X-Correlation-ID` y `Retry-After`;
- no sigue redirects del upstream;
- no registra cuerpos ni secretos;
- devuelve `UPSTREAM_UNAVAILABLE` con correlation ID ante fallo de transporte;
- lee la URL de FastAPI únicamente en código de servidor;
- no transforma errores de dominio ni resultados.

`/api/v1/health` no se inventa: el contrato real de health vive en `/health`.

### Cliente API tipado

Se mantienen tipos manuales derivados de los schemas Pydantic para:

- health;
- inquiries: create, list y detail;
- agent runs: create, list, detail, events, result y retry;
- opportunity detail;
- customer memory;
- error envelope;
- resultados y referencias comerciales.

Un único wrapper `fetch` debe:

- formar query params omitiendo valores nulos;
- serializar JSON solo cuando exista body;
- adjuntar `Idempotency-Key` explícitamente;
- usar rutas same-origin;
- convertir el envelope de error en `ApiError` tipado;
- rechazar contenido exitoso inesperado;
- conservar correlation ID y detalles seguros.

No se añaden Axios, Zod, React Query, librería de estado global ni generación
OpenAPI. La divergencia se controla con centralización y pruebas de contrato.

### Configuración

| Variable | Visibilidad | Uso |
|---|---|---|
| `FASTAPI_BASE_URL` | server-only | URL interna del servicio FastAPI |
| `DEMO_MODE` | server-only | condición de ejecución demo |

Reglas:

- ninguna variable usa prefijo `NEXT_PUBLIC_`;
- `FASTAPI_BASE_URL` acepta únicamente HTTP(S);
- localmente usa `http://127.0.0.1:8000` por defecto;
- Compose fija `http://api:8000`;
- Qwen y sus secretos permanecen solo en `api`.

### Delta backend autorizado

El único cambio backend es añadir `tool_name` a `_public_event_payload`.

Debe comprobarse para eventos de inicio, éxito, fallo y rechazo, conservando
fuera de la respuesta:

- `arguments` e inputs equivalentes;
- `result` y outputs completos;
- secretos;
- correos u otros datos personales;
- payload crudo del proveedor.

No se crea campo nuevo: `tool_name` vive dentro de `PublicEvent.payload`.

### Docker, Make y CI

- Dockerfile web multi-stage con Node.js 22;
- `npm ci` y salida standalone;
- usuario no root;
- healthcheck web mediante `/api/health`;
- servicio `web` en Compose, dependiente de `api` saludable;
- API sin cambios en su comando de un worker;
- targets Make separados y combinados;
- CI web con install, lint, typecheck, test y build.

## Estructura prevista

```text
apps/web/
├── public/
├── src/
│   ├── app/
│   │   ├── api/health/route.ts
│   │   ├── api/v1/[...path]/route.ts
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   └── lib/
│       ├── api/client.ts
│       ├── api/types.ts
│       └── server/
│           ├── config.ts
│           └── proxy.ts
├── tests/
├── Dockerfile
├── eslint.config.mjs
├── next.config.ts
├── package.json
├── package-lock.json
├── postcss.config.mjs
├── tsconfig.json
└── vitest.config.ts
```

No se crea `packages/`, SDK separado ni design system general.

## Dependencias mínimas

### Runtime

- `next` 16.2.x;
- `react` y `react-dom` 19.2.x.

### Desarrollo

- TypeScript 5.9.x y tipos Node/React;
- Tailwind CSS 4.1.x y plugin PostCSS;
- ESLint 9.39.x y `eslint-config-next` 16.2.x;
- Vitest 4.0.x.

### Precisiones de compatibilidad

La revisión de implementación corrigió dos supuestos:

1. ESLint 10 no es todavía compatible con los plugins incluidos por
   `eslint-config-next` 16.2. Se fija ESLint 9.39.5.
2. Next.js 16 usa `jsx: react-jsx`; no se fuerza `jsx: preserve`.

Estas precisiones no cambian arquitectura ni alcance.

## Estrategia de pruebas

### Unitarias

- validación y defaults de configuración;
- construcción de query params;
- serialización condicional de JSON;
- error tipado y contenido inesperado.

### Contrato del proxy

- mapping especial de health;
- catch-all versionado para GET y POST;
- método, query y body;
- idempotencia y allowlist de headers;
- status y headers seguros de respuesta;
- indisponibilidad del upstream sin filtrar internals.

### Contrato backend

- `tool_name` visible en los cuatro resultados de tool;
- inputs, outputs, secretos y PII ausentes.

### Gates

```bash
make check-web
make check-api
make check
docker compose up --build
```

Además se inspecciona el bundle para confirmar que no contiene la URL interna
configurada de FastAPI.

## Criterios de aceptación del bloque

| ID | Criterio verificable |
|---|---|
| B1-AC-01 | `apps/web` instala reproduciblemente con `npm ci`. |
| B1-AC-02 | Node 22 está fijado para local, CI y Docker. |
| B1-AC-03 | Next usa App Router y salida standalone. |
| B1-AC-04 | TypeScript estricto y alias `@/*` pasan. |
| B1-AC-05 | Tailwind 4 compila en producción. |
| B1-AC-06 | ESLint termina sin warnings. |
| B1-AC-07 | `/` renderiza el shell sin depender de FastAPI. |
| B1-AC-08 | El shell identifica claramente el entorno demo. |
| B1-AC-09 | Skip link, foco y estructura semántica existen. |
| B1-AC-10 | El layout funciona desde 360 px. |
| B1-AC-11 | `/api/health` llega a FastAPI `/health`. |
| B1-AC-12 | `/api/v1/*` preserva la versión del contrato. |
| B1-AC-13 | GET y POST preservan método y query. |
| B1-AC-14 | POST preserva cuerpo e `Idempotency-Key`. |
| B1-AC-15 | Solo se reenvían headers aprobados. |
| B1-AC-16 | Status y headers seguros se conservan. |
| B1-AC-17 | Un fallo de transporte produce envelope seguro y correlation ID. |
| B1-AC-18 | `FASTAPI_BASE_URL` no es pública ni aparece en el bundle. |
| B1-AC-19 | El cliente cubre todos los endpoints P0 existentes. |
| B1-AC-20 | `ApiError` conserva code, status, details y correlation ID. |
| B1-AC-21 | `payload.tool_name` se expone en eventos de tool. |
| B1-AC-22 | Arguments, outputs, secretos y PII continúan filtrados. |
| B1-AC-23 | Compose inicia web y API saludable con un worker. |
| B1-AC-24 | Frontend y suite backend completa pasan sin regresión. |

## Riesgos y mitigaciones

| Riesgo | Nivel | Mitigación |
|---|---:|---|
| URL interna filtrada al browser | Alto | variable server-only y test/inspección de bundle |
| proxy se convierte en BFF con reglas | Alto | reenvío transparente y adaptador health único |
| contratos TypeScript divergen | Medio | archivo central y contract tests |
| dependencia innecesaria | Medio | lista mínima y lockfile |
| proxy filtra payload o headers | Alto | allowlists y errores propios sin detalles internos |
| Compose altera el worker API | Alto | Dockerfile API intacto y prueba de contrato |
| shell adelanta pantallas | Medio | una sola ruta temporal sin datos de negocio |
| Node local distinto de CI | Medio | engines, Docker y CI fijados en Node 22 |

## Fuera de alcance

- cockpit y lista real de runs;
- formulario de inquiry y UC-001;
- creación encadenada de inquiry/run;
- polling y timeline;
- workspace y resultado comercial;
- retry visual;
- autenticación, usuarios, roles o multitenencia operativa;
- envío, aprobación, reserva o sincronización;
- CRM, calendario, ERP o inventario externos;
- PDF, métricas o analytics;
- WebSockets, SSE, Redis, Celery o múltiples workers;
- PostgreSQL;
- endpoints, migraciones, prompts, tools u orquestación nuevos.

## Archivos afectados

### Nuevos

- `apps/web/**`;
- `.github/workflows/web-ci.yml`;
- `apps/api/tests/test_public_event_contract.py`;
- `docs/implementation/070-sprint-3-block-1-web-foundation.md`.

### Modificados

- `apps/api/app/api/v1/product.py`;
- `docker-compose.yml`;
- `Makefile`;
- `.env.example`;
- `README.md`;
- `VERIFICATION.md`;
- `CHANGELOG.md`.

No se modifican modelos, tablas, migraciones, schemas Pydantic, endpoints,
servicios, tools, prompts ni el orquestador.

## Condición de cierre

El Bloque 1 solo puede declararse cerrado después de:

1. completar B1-AC-01 a B1-AC-24;
2. ejecutar Compose desde entorno limpio;
3. verificar un worker API efectivo;
4. aprobar CI y revisión de PR;
5. fusionar y revalidar `main`.

Hasta entonces el resultado es candidato de implementación, no cierre del
bloque ni del Sprint 3.
