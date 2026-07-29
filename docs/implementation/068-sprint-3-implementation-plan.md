# Plan de implementación del Sprint 3

## Principio

Construir verticalmente sobre el contrato backend existente. Cada bloque debe
dejar una parte demostrable y probada sin iniciar el siguiente antes de cerrar
su documentación específica.

## Bloque 0 — Documentación

### Objetivo

Congelar dirección de producto, alcance, experiencia, aceptación y DoD.

### Trabajo

- registrar la transición a validación comercial;
- aprobar el charter;
- aprobar arquitectura de experiencia;
- aprobar bloques y riesgos;
- aprobar criterios de aceptación y DoD;
- actualizar backlog, README y contrato de eventos.

### Salida

Documentación de Sprint 3 aprobada y fusionada. No se modifica código.

## Bloque 1 — Fundación web y contrato

### Objetivo

Crear una aplicación Next.js que se comunique de forma segura y tipada con el
backend.

### Trabajo

- crear `apps/web`;
- configurar App Router, TypeScript estricto y Tailwind;
- definir variables públicas y server-only;
- implementar proxy `/api/v1`;
- crear tipos y cliente HTTP centralizado;
- modelar error envelope;
- añadir shell, tokens visuales y navegación;
- añadir `tool_name` a la allowlist pública del backend;
- cubrir el delta con prueba de contrato;
- añadir web al flujo local y Compose sin alterar el worker único de API.

### Salida

Web arranca, health funciona vía proxy y los contratos críticos están probados.

### Exclusiones

- pantallas de negocio completas;
- librería de estado global;
- generación automática obligatoria desde OpenAPI;
- cambios backend adicionales.

## Bloque 2 — Cockpit y entrada

### Objetivo

Crear y abrir una ejecución real desde la interfaz.

### Trabajo

- listar runs recientes;
- implementar estados vacío, carga y error;
- crear formulario manual;
- cargar entrada UC-001;
- generar claves idempotentes independientes;
- encadenar creación de inquiry y run;
- prevenir doble submit;
- navegar a `/runs/[runId]`;
- probar replay de transporte y doble clic.

### Salida

El usuario inicia el flujo sin terminal ni Swagger.

## Bloque 3 — Ejecución observable

### Objetivo

Hacer comprensible el progreso desde `queued` hasta estado terminal.

### Trabajo

- obtener detalle del run;
- implementar polling incremental;
- acumular eventos sin huecos ni duplicados;
- traducir pasos y tools a labels;
- agrupar timeline;
- detener polling en terminal;
- presentar `needs_review`, `completed` y `failed`;
- mostrar error seguro y correlation ID;
- implementar retry autorizado y vínculo entre intentos.

### Salida

El workspace muestra progreso real, tools y recuperación controlada.

## Bloque 4 — Resultado comercial

### Objetivo

Convertir `RunResult` en un workspace de revisión comercial.

### Trabajo

- mensaje y análisis;
- faltantes;
- recomendación;
- stock disponible expuesto por el resultado;
- quote y formato monetario;
- propuesta y borrador;
- oportunidad y seguimiento;
- memoria previa y nueva;
- warnings y secciones parciales;
- labels explícitos de demo y revisión humana.

### Salida

UC-001 puede explicarse visualmente de extremo a extremo.

## Bloque 5 — Integración y cierre

### Objetivo

Dejar Sprint 3 reproducible y listo para el gate de validación comercial.

### Trabajo

- responsive desde 360 px;
- accesibilidad;
- pruebas unitarias, integración y flujo crítico;
- Compose integrado;
- documentación local;
- prueba determinista sin Qwen live;
- smoke opcional con Qwen live;
- revisión de promesas visuales;
- evidencias de aceptación;
- cierre y revalidación en `main`.

### Salida

MVP frontend demostrable localmente y candidato a Sprint 4.

## Orden recomendado de ramas

1. `docs/sprint3-frontend-plan`
2. `feat/sprint3-web-foundation`
3. `feat/sprint3-inquiry-entry`
4. `feat/sprint3-run-observability`
5. `feat/sprint3-commercial-result`
6. `test/sprint3-frontend-closeout`

## Estrategia de pruebas

| Nivel | Cobertura mínima |
|---|---|
| Unitario | formatos, mappings, idempotencia cliente, reducer de eventos |
| Componente | formulario, estados, timeline, secciones parciales |
| Contrato | proxy, envelopes, `tool_name`, URLs y status codes |
| Integración | create inquiry → create run → poll → result |
| E2E determinista | UC-001 completo con fake Qwen y backend real |
| Live opcional | compatibilidad Qwen, no bloqueante para CI |

## Riesgos de ejecución

| Riesgo | Nivel | Mitigación |
|---|---:|---|
| frontend se convierte en CRM | Alto | tres rutas y solo lectura |
| acabado visual consume el sprint | Alto | tokens mínimos y componentes limitados |
| polling duplicado | Medio | una instancia, cursor y requests no solapados |
| comandos duplicados | Alto | claves persistentes por intención |
| UI inventa datos | Alto | adapters sin reglas de negocio |
| contrato TypeScript diverge | Medio | tipos centralizados y contract tests |
| demo depende de Qwen live | Alto | fake determinista; live opcional |
| `needs_review` parece error | Alto | estado semántico propio |
| Sprint 4 entra en Sprint 3 | Alto | excluir despliegue y materiales |

## Criterio para modificar alcance

Un cambio entra únicamente si:

1. corrige un defecto que impide ejecutar, observar o revisar UC-001;
2. no introduce integración externa;
3. se documenta antes de implementarse;
4. mantiene las exclusiones del charter.

Lo demás vuelve al backlog de validación.
