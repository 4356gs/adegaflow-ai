# Sprint 3 — Aceptación y Definition of Done

## Escenarios de aceptación

| ID | Criterio verificable |
|---|---|
| S3-AT-001 | La aplicación abre en modo demo sin autenticación externa. |
| S3-AT-002 | El cockpit lista runs reales con estado, empresa, mercado y fecha cuando existan. |
| S3-AT-003 | El usuario introduce un mensaje o carga UC-001 sin resultados hardcodeados. |
| S3-AT-004 | Una acción crea inquiry y run con claves idempotentes independientes. |
| S3-AT-005 | Doble clic o replay equivalente no duplica inquiry ni run. |
| S3-AT-006 | El workspace muestra paso actual y eventos incrementales mediante `after_sequence`. |
| S3-AT-007 | La timeline identifica tools reales y distingue inicio, éxito, rechazo y fallo. |
| S3-AT-008 | El polling no solapa requests, no duplica eventos y se detiene en terminal. |
| S3-AT-009 | El resultado muestra todas las secciones disponibles de `RunResult`. |
| S3-AT-010 | Una sección ausente o parcial no rompe las demás. |
| S3-AT-011 | `needs_review` se presenta como resultado esperado pendiente de revisión. |
| S3-AT-012 | No existe control que prometa enviar, aprobar, reservar o sincronizar externamente. |
| S3-AT-013 | Un fallo recuperable ofrece retry; el nuevo run enlaza al original. |
| S3-AT-014 | Un fallo no recuperable no ofrece retry. |
| S3-AT-015 | Los errores muestran mensaje seguro y correlation ID, sin internals. |
| S3-AT-016 | La memoria diferencia hechos de la inquiry actual y previos mediante `source_inquiry_id`. |
| S3-AT-017 | El flujo principal funciona desde 360 px hasta escritorio. |
| S3-AT-018 | El navegador solo accede al proxy same-origin y no recibe secretos. |
| S3-AT-019 | El escenario completo se comprende visualmente en menos de dos minutos. |
| S3-AT-020 | La aplicación integrada se levanta con comandos documentados sin editar código. |
| S3-AT-021 | El E2E determinista usa backend real y fake Qwen; no usa resultados de UI simulados. |
| S3-AT-022 | La exposición de `tool_name` conserva filtrados inputs, outputs, secretos y datos personales. |

## Evidencia requerida

Cada criterio debe enlazar antes del cierre a una evidencia:

- test automatizado;
- captura o grabación breve;
- comando reproducible;
- revisión manual documentada.

Una captura sola no demuestra idempotencia, contrato ni persistencia. Un test
solo no demuestra comprensión visual o responsive.

## Definition of Done funcional

- las tres rutas P0 existen;
- UC-001 se inicia desde la UI;
- estado y eventos se leen del backend;
- el resultado terminal se renderiza sin datos inventados;
- secciones parciales son seguras;
- retry respeta `retryable`;
- propuesta y correo se identifican como borradores;
- no existen mutaciones fuera de alcance.

## Definition of Done técnica

- TypeScript estricto aprobado;
- lint y build frontend aprobados;
- tests frontend aprobados;
- Ruff y mypy backend aprobados;
- suite backend existente sigue aprobada;
- test de contrato de `tool_name` aprobado;
- E2E determinista aprobado;
- Compose levanta web y API;
- API opera con exactamente un worker;
- no hay secretos en repositorio ni bundle del navegador;
- `git diff --check` aprobado.

La cobertura frontend se medirá para detectar áreas sin prueba, pero Sprint 3 no
introduce un porcentaje arbitrario como sustituto de los escenarios críticos.

## Definition of Done UX

- layout funcional desde 360 px;
- navegación por teclado;
- foco visible;
- labels de controles;
- contraste y estados no dependientes solo de color;
- carga, vacío, parcial, error y terminal poseen tratamiento explícito;
- timeline comprensible sin JSON;
- importes y fechas formateados;
- datos demo y revisión humana visibles.

## Definition of Done documental

- README actualizado;
- setup web documentado;
- variables de entorno documentadas;
- comandos de ejecución y prueba documentados;
- backlog actualizado;
- contrato de eventos actualizado;
- evidencia S3-AT-001 a S3-AT-022 registrada;
- riesgos residuales documentados;
- cierre post-merge revalidado en `main`.

## Gate de cierre

Sprint 3 no se declara cerrado hasta que:

1. todos los criterios S3-AT tengan evidencia;
2. no existan fallos bloqueantes;
3. el flujo determinista completo pase desde un entorno limpio;
4. la aplicación haya sido revisada en móvil y escritorio;
5. la documentación y el código hayan sido fusionados;
6. `main` se haya revalidado.

## Gate hacia Sprint 4

Sprint 4 puede comenzar únicamente después del cierre de Sprint 3. Su objetivo
será preparar despliegue controlado y validación comercial, no construir la
solución completa.

## No se considera terminado

- mock visual sin backend;
- JSON presentado como interfaz;
- resultados hardcodeados;
- botones que no ejecutan su promesa;
- dependencia obligatoria de Qwen live para probar el flujo;
- frontend que requiere acceder directamente a FastAPI;
- ampliación a autenticación, SaaS o integraciones externas;
- diseño atractivo sin idempotencia, errores y estados parciales correctos.
