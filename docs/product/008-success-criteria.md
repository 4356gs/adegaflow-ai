# Criterios de éxito

## Éxito funcional del MVP

El MVP se considera funcionalmente exitoso cuando cumple todos los criterios P0:

| ID | Criterio | Verificación |
|---|---|---|
| SC-001 | Recibe una consulta comercial no estructurada | Entrada manual o escenario demo |
| SC-002 | Detecta una oportunidad B2B internacional | Clasificación visible |
| SC-003 | Extrae los datos principales | Resultado estructurado validado |
| SC-004 | Identifica información faltante | Lista explícita, sin inventar datos |
| SC-005 | Recupera memoria del comprador | Historial mostrado |
| SC-006 | Invoca al menos tres herramientas | Registro de ejecuciones |
| SC-007 | Consulta catálogo y stock | Resultados trazables |
| SC-008 | Recomienda productos disponibles | Validación contra datos semilla |
| SC-009 | Genera una propuesta coherente | Cantidades y precios consistentes |
| SC-010 | Redacta respuesta en el idioma adecuado | Borrador en inglés |
| SC-011 | Registra la oportunidad | Registro persistente en CRM simulado |
| SC-012 | Crea seguimiento a siete días | Tarea persistente |
| SC-013 | Guarda memoria comercial | Preferencias recuperables |
| SC-014 | Muestra el historial de acciones | Línea de tiempo o panel |
| SC-015 | Utiliza Qwen Cloud de forma central | Evidencia en ejecución y documentación |
| SC-016 | Completa el flujo de demo sin acciones externas | Revisión manual final |

## Calidad mínima de la demo

- el escenario principal puede repetirse;
- los datos resultantes son coherentes entre pantallas;
- los errores no exponen trazas sensibles;
- las claves permanecen fuera del repositorio;
- el flujo crítico cuenta con pruebas;
- la aplicación puede levantarse mediante instrucciones documentadas;
- la interfaz permite comprender qué hizo el agente en menos de dos minutos;
- la demostración no depende de editar código en directo.

## Criterios narrativos

La demo debe dejar claro que:

1. el problema es comercial y operativo, no meramente conversacional;
2. la especialización en bodegas aporta contexto;
3. Qwen Cloud interpreta y coordina acciones;
4. las herramientas ejecutan trabajo empresarial;
5. la memoria mejora la continuidad;
6. la trazabilidad permite supervisión humana;
7. el producto puede evolucionar hacia una oferta comercial.

## Umbrales internos de preparación

Antes de grabar o presentar:

- 10 ejecuciones consecutivas del escenario principal sin fallo bloqueante;
- 100 % de las recomendaciones consistentes con el stock;
- 0 secretos detectados en el repositorio;
- 0 enlaces o botones que prometan acciones reales no implementadas;
- 1 ruta de fallback probada para fallo del modelo;
- 1 ruta de fallback probada para fallo de una herramienta.

Estos umbrales son objetivos internos del proyecto, no métricas oficiales del hackathon.

## No se considerará éxito

- una demo basada únicamente en texto generado;
- un flujo con resultados hardcodeados que no use Qwen Cloud;
- una interfaz atractiva sin ejecución real de herramientas;
- una arquitectura compleja que no complete el caso de uso;
- una propuesta que dependa de integraciones externas no controladas.
