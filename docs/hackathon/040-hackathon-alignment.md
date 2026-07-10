# Alineación con el hackathon Qwen Cloud

## Estado de referencia

Revisión realizada el 2026-07-10 sobre las páginas oficiales de Devpost y la documentación oficial de Qwen Cloud.

## Track seleccionado

**Track 4 — Autopilot Agent**

AdegaFlow AI coincide directamente con el objetivo del track:

- automatiza un flujo empresarial real de extremo a extremo;
- procesa una entrada ambigua;
- invoca tools;
- mantiene un punto de revisión humana;
- prioriza preparación para producción sobre una demo puramente conversacional.

La memoria de comprador refuerza el producto, pero no se presentará como candidatura principal de MemoryAgent.

## Tracks descartados

- **MemoryAgent:** la memoria es importante, pero no es el núcleo competitivo.
- **Agent Society:** no se implementará multiagente artificial sin demostrar mejora frente a un agente único.
- **AI Showrunner:** no corresponde al problema.
- **EdgeAgent:** no existe componente físico.

## Requisitos de candidatura

- repositorio público;
- licencia open source visible;
- código, assets e instrucciones de funcionamiento;
- prueba de backend desplegado en Alibaba Cloud;
- diagrama de arquitectura;
- video público de menos de tres minutos;
- descripción de funciones;
- identificación del track;
- demo o acceso de prueba disponible durante evaluación.

## Fechas oficiales

- cierre de candidaturas: **20 de julio de 2026, 14:00 PDT**;
- evaluación: 28 de julio al 11 de agosto de 2026;
- anuncio estimado de ganadores: 17 de agosto de 2026.

## Criterios de evaluación

| Criterio | Peso | Respuesta de AdegaFlow AI |
|---|---:|---|
| Profundidad técnica e ingeniería | 30 % | tool calling, validación tipada, tools propias, fallbacks, trazabilidad |
| Innovación y creatividad IA | 30 % | agente vertical, flujo acotado, memoria, autonomía controlada |
| Valor e impacto | 25 % | problema comercial real de pymes y exportación |
| Presentación y documentación | 15 % | UI de flujo, arquitectura, README, video y documentación GitHub |

## Estrategia competitiva

### Profundidad técnica

No se perseguirá complejidad ornamental. La profundidad se demostrará mediante:

- tool calling real;
- contratos JSON;
- separación IA/dominio;
- validación Pydantic;
- idempotencia;
- persistencia de runs;
- fallback;
- trazabilidad;
- despliegue reproducible.

### Innovación

La novedad se expresa en el flujo especializado:

> consulta internacional → análisis → memoria → catálogo → stock → propuesta → CRM → seguimiento.

### Impacto

Se explicará el coste operativo de:

- respuestas tardías;
- información dispersa;
- oportunidades sin seguimiento;
- dependencia de personas clave.

No se presentarán cifras de ahorro sin validación.

### Presentación

El video debe mostrar acciones, no explicar arquitectura durante dos minutos. Orden recomendado:

1. mensaje del distribuidor;
2. ejecución visible;
3. tools y datos extraídos;
4. propuesta y correo;
5. CRM, seguimiento y memoria;
6. arquitectura y cierre.

## Riesgo estratégico

El sitio oficial resalta sistemas multiagente y producción, pero el track Autopilot no exige múltiples agentes. Implementar una “sociedad” de agentes reduciría confiabilidad y exigiría una comparación medible contra un baseline de agente único.

## Fuentes oficiales

- [Hackathon overview](https://qwencloud-hackathon.devpost.com/)
- [Official rules](https://qwencloud-hackathon.devpost.com/rules)
- [Hackathon resources](https://qwencloud-hackathon.devpost.com/resources)
- [Qwen Cloud function calling](https://docs.qwencloud.com/developer-guides/text-generation/function-calling)
- [Qwen structured output](https://help.aliyun.com/en/model-studio/qwen-structured-output)
- [Qwen OpenAI-compatible chat API](https://docs.qwencloud.com/api-reference/chat/openai-chat)
