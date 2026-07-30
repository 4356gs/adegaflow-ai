# Dirección de producto — MVP para validación comercial

- **Estado:** Approved
- **Fecha:** 2026-07-29
- **Baseline técnico:** `d24473ce82d2443c28c010e0e89a9828026648fd`
- **Decisores:** Equipo de producto AdegaFlow AI

## Decisión

AdegaFlow AI deja de optimizarse para una competición. El objetivo vigente es:

> Construir un MVP demostrable para validar con bodegas y distribuidores si el
> problema, la propuesta de valor y el flujo comercial justifican desarrollar
> una solución completa.

El trabajo técnico cerrado en Sprint 2 se conserva. El cambio afecta las
prioridades, la experiencia de usuario, el criterio de éxito y la secuencia
posterior, no el dominio ni los contratos backend ya validados.

Este documento sustituye cualquier orientación futura hacia hackathon,
submission, jueces o premios. Los documentos anteriores conservan valor como
registro histórico de las decisiones tomadas en su momento.

## Hipótesis que debe validar el MVP

### Problema

Responsables comerciales de bodegas y distribuidores pierden tiempo y
consistencia al convertir consultas B2B no estructuradas en recomendaciones,
propuestas, oportunidades y seguimientos.

### Propuesta de valor

Una experiencia asistida por IA puede concentrar ese trabajo en un flujo
trazable, sujeto a revisión humana y adaptado al contexto comercial del vino.

### Adopción

El usuario objetivo puede entender el flujo sin explicación técnica extensa y
considera útil probarlo con un escenario o datos propios.

### Disposición a avanzar

Al menos una empresa relevante acepta discutir un piloto, acceso controlado a
datos o condiciones económicas. Una valoración positiva sin compromiso no
valida inversión adicional.

## Usuario y contexto de validación

Usuario principal:

- responsable comercial o de exportación de una bodega pequeña o mediana;
- responsable de ventas de un distribuidor especializado;
- persona que hoy coordina consultas, disponibilidad, propuesta y seguimiento.

Contexto inicial:

- demostración guiada;
- una organización ficticia;
- datos verosímiles y explícitamente identificados como demo;
- un caso principal estable;
- revisión humana antes de cualquier acción externa.

## Criterios de éxito comercial

La fase de validación posterior al Sprint 4 debe producir evidencia observable:

| Señal | Umbral inicial |
|---|---:|
| Demostraciones con empresas del perfil objetivo | 5–10 |
| Empresas que reconocen claramente el problema | ≥3 |
| Empresas interesadas en segunda conversación o piloto | ≥2 |
| Empresas dispuestas a discutir precio, datos o condiciones de piloto | ≥1 |

Estos umbrales son criterios de decisión, no promesas de mercado. Se revisarán
con evidencia de entrevistas.

## Decisión posterior

Solo se diseñará una solución completa si la validación aporta evidencia
suficiente. La decisión deberá distinguir:

- continuar con piloto conectado;
- iterar la propuesta de valor;
- cambiar el segmento;
- detener la inversión.

## Consecuencias para Sprint 3

- la interfaz se diseña para un cliente potencial, no para un público técnico;
- la trazabilidad explica trabajo y control, sin exponer JSON ni internals;
- el resultado se presenta como borrador comercial revisable;
- no se añaden autenticación, multitenencia ni integraciones externas;
- no se construye un CRM o ERP;
- no se inventan métricas de ahorro o retorno;
- el alcance se limita a convertir UC-001 en una experiencia web creíble.

## Consecuencias para Sprint 4

Sprint 4 se orientará a:

- despliegue controlado;
- datos y guion de demostración;
- captura estructurada de feedback;
- materiales comerciales mínimos;
- preparación de la fase de validación.

No se incluye todavía una solución productiva completa.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| confundir elogios con validación | exigir compromisos observables |
| construir SaaS antes de probar demanda | mantener exclusiones y gate de inversión |
| usar datos demo poco creíbles | revisar escenario con vocabulario sectorial |
| prometer automatización externa inexistente | mostrar siempre borrador y revisión humana |
| sesgo por demostrar solo a contactos favorables | seleccionar perfiles variados del segmento |
