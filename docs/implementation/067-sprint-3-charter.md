# Sprint 3 — Charter de experiencia frontend demostrable

## Estado

- **Sprint:** 3 — Experiencia frontend
- **Estado:** Approved for implementation
- **Baseline:** Sprint 2 cerrado en `d24473c`
- **Código de producto:** No iniciado
- **Objetivo único:** construir una aplicación web responsive que permita
  ejecutar, observar y revisar UC-001 de extremo a extremo sobre el backend
  existente.

## Resultado esperado

Una persona no técnica puede:

1. abrir AdegaFlow AI en modo demo;
2. introducir una consulta o cargar el escenario canónico;
3. iniciar una ejecución real mediante la API;
4. comprender el progreso y las herramientas utilizadas;
5. revisar análisis, recomendación, stock, cotización y artefactos;
6. ver la oportunidad, el seguimiento y la memoria persistidos;
7. distinguir un resultado `needs_review` de un fallo;
8. reintentar únicamente un fallo que el backend marque como recuperable.

La experiencia debe demostrar valor comercial y supervisión humana. No debe
simular funciones que el backend no ejecuta.

## Alcance P0

### Aplicación

- Next.js con App Router;
- TypeScript estricto;
- Tailwind CSS;
- diseño responsive;
- acceso demo sin autenticación;
- proxy same-origin hacia FastAPI;
- cliente API tipado y centralizado.

### Superficies

| Ruta | Responsabilidad |
|---|---|
| `/` | cockpit de consultas y ejecuciones recientes |
| `/inquiries/new` | entrada manual y escenario UC-001 |
| `/runs/[runId]` | progreso, trazabilidad y resultado comercial |

No se crearán páginas independientes para catálogo, CRM, clientes, métricas o
artefactos. Esos elementos son secciones del workspace del run.

### Flujo

- crear inquiry con `Idempotency-Key`;
- crear agent run con otra clave;
- conservar cada clave durante reintentos de transporte;
- navegar al workspace del run;
- consultar estado y eventos con `after_sequence`;
- detener polling al alcanzar estado terminal;
- obtener el resultado comercial terminal;
- mostrar resultados parciales y warnings;
- crear retry auditable cuando `retryable=true`.

### Contenido visible

- mensaje original;
- idioma, intención y datos extraídos;
- información faltante;
- pasos y herramientas utilizadas;
- recomendación y disponibilidad;
- cotización;
- propuesta;
- borrador de correo;
- oportunidad;
- seguimiento;
- memoria previa y nueva;
- advertencias;
- estado de revisión humana;
- error seguro y correlation ID cuando proceda.

### Calidad

- pruebas unitarias de componentes y utilidades críticas;
- pruebas de integración del cliente y proxy;
- prueba del flujo principal con backend determinista;
- accesibilidad básica verificable;
- ejecución integrada con Docker Compose;
- comandos locales documentados.

## Delta backend autorizado

Se autoriza un único cambio de contrato:

- exponer `tool_name` en el payload público de eventos cuando exista.

Los eventos internos ya persisten ese dato. La allowlist pública actual lo
elimina, impidiendo identificar la herramienta real desde el frontend.

La implementación deberá:

- añadir solo `tool_name` a la allowlist pública;
- probar eventos de inicio, éxito, fallo y rechazo;
- conservar filtrados argumentos, resultados completos, secretos y datos
  personales;
- no crear endpoint, tabla, migración ni schema de negocio adicional.

Ningún otro cambio backend entra en Sprint 3 sin actualizar y aprobar primero
esta documentación.

## Fuera de alcance

- autenticación, roles o usuarios;
- multitenencia operativa;
- edición, aprobación o rechazo persistente de artefactos;
- envío de correo;
- CRM, calendario, ERP o inventario externos;
- reserva o modificación de stock;
- PDF;
- panel analítico o métricas de ahorro;
- WebSockets, SSE o streaming de tokens;
- Redis, Celery o cola durable;
- múltiples workers;
- PostgreSQL;
- nuevos escenarios de negocio;
- CRUD de catálogo, clientes u oportunidades;
- cambios en prompts, reglas comerciales, tools u orquestación;
- despliegue público y materiales comerciales de Sprint 4.

## Restricciones vinculantes

- la documentación se aprueba antes de programar;
- la UI renderiza datos del contrato, no inferencias inventadas;
- `needs_review` es un resultado esperado;
- ninguna acción visual promete enviar, aprobar, reservar o sincronizar;
- una sola instancia de polling opera por workspace;
- el navegador no conoce direcciones internas ni secretos de FastAPI;
- el backend continúa con SQLite, cola local y un solo worker.

## Gate de inicio

La implementación comienza únicamente cuando:

- `012-commercial-validation-direction.md`;
- `031-frontend-experience.md`;
- `067-sprint-3-charter.md`;
- `068-sprint-3-implementation-plan.md`;
- `069-sprint-3-acceptance-and-definition-of-done.md`;

han sido revisados, aprobados y fusionados en `main`.
