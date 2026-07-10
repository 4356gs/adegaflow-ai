# Plan de entrega hasta el hackathon

## Restricción

Fecha de referencia: 2026-07-10.  
Fecha límite: 2026-07-20 a las 14:00 PDT.

El plan evita depender del último día.

## Calendario

| Fecha | Objetivo único | Salida obligatoria |
|---|---|---|
| 10 jul | Cerrar arquitectura | Sprint 1 y ADR aceptados |
| 11 jul | Probar Qwen Cloud | Llamada, JSON y tool calling funcionando |
| 12 jul | Implementar datos y tools de lectura | Catálogo, stock, memoria |
| 13 jul | Completar orquestador | Flujo backend principal |
| 14 jul | Completar acciones y artefactos | Cotización, CRM, seguimiento, propuesta |
| 15 jul | Construir interfaz principal | Flujo visible de extremo a extremo |
| 16 jul | Integración y fallbacks | Camino feliz y errores críticos |
| 17 jul | Desplegar en Alibaba Cloud | URL pública y evidencia |
| 18 jul | Pruebas, README y guion | Candidato congelado |
| 19 jul | Grabar video y enviar | Submission completada |
| 20 jul | Solo contingencia | Corrección menor, no nuevas funciones |

## Gate 1 — 11 de julio

Debe funcionar:

- autenticación con Qwen Cloud;
- salida JSON válida;
- una tool invocada;
- registro básico de ejecución.

Si falla, se reduce el diseño antes de continuar.

## Gate 2 — 14 de julio

Debe existir un flujo backend sin frontend:

- mensaje;
- extracción;
- catálogo;
- stock;
- cotización;
- propuesta;
- CRM;
- seguimiento;
- memoria.

## Gate 3 — 17 de julio

Debe existir:

- despliegue en Alibaba Cloud;
- datos persistentes;
- interfaz utilizable;
- URL de prueba;
- instrucciones reproducibles.

## Freeze

Después del 18 de julio:

- no se añaden P1;
- no se cambia el modelo de datos salvo defecto bloqueante;
- no se cambia el framework;
- no se introduce MCP, vector DB o agentes adicionales;
- solo se corrigen fallos.

## Funciones sacrificables

En este orden:

1. PDF.
2. panel de métricas.
3. edición avanzada.
4. múltiples escenarios.
5. animaciones.
6. autenticación.

No se sacrifican:

- Qwen Cloud;
- tool calling;
- trazabilidad;
- propuesta;
- CRM;
- seguimiento;
- memoria;
- despliegue en Alibaba Cloud.
