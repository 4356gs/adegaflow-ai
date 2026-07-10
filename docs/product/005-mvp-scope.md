# Alcance del MVP

## Objetivo del MVP

Demostrar que AdegaFlow AI puede procesar de principio a fin una consulta comercial B2B para una bodega gallega mediante Qwen Cloud y herramientas estructuradas.

## Alcance funcional obligatorio — P0

### Acceso y entrada

- acceso demo sin sistema completo de cuentas;
- bandeja simple de consultas;
- entrada manual de un mensaje comercial;
- carga de un escenario predefinido.

### Comprensión

- detección de idioma;
- clasificación de intención;
- identificación de oportunidad B2B;
- extracción estructurada de:
  - empresa o comprador;
  - país o mercado;
  - tipo de producto;
  - volumen;
  - canal;
  - fecha objetivo;
  - presupuesto, cuando exista;
  - solicitud de muestras;
  - requisitos mencionados;
- identificación explícita de datos faltantes;
- asignación de prioridad con una justificación simple.

### Contexto y memoria

- recuperación de historial del comprador;
- uso de preferencias previas en la recomendación;
- persistencia de nueva memoria comercial;
- visualización del contexto recuperado y guardado.

### Herramientas empresariales simuladas

- búsqueda de catálogo;
- consulta de stock;
- detalle de producto;
- cálculo básico de propuesta;
- creación de oportunidad en CRM simulado;
- creación de tarea de seguimiento;
- generación de propuesta;
- creación de borrador de correo.

### Resultado comercial

- recomendación de al menos dos productos adecuados;
- propuesta con cantidades, precios de demostración y condiciones identificadas como preliminares;
- borrador de respuesta en el idioma apropiado;
- registro de la oportunidad;
- seguimiento programado;
- historial de acciones ejecutadas.

### Trazabilidad

- secuencia visible de pasos;
- herramientas invocadas;
- entradas y salidas resumidas;
- estado de cada acción;
- errores controlados;
- indicación de qué elementos requieren revisión humana.

### IA

- Qwen Cloud debe intervenir de forma central en:
  - interpretación;
  - planificación o selección de herramientas;
  - generación estructurada;
  - redacción de la respuesta.

## Datos de demostración

- una bodega ficticia;
- catálogo inicial de seis tipos de producto;
- stock coherente con el catálogo;
- varios compradores ficticios;
- historial y preferencias;
- oportunidades y seguimientos simulados;
- precios identificados como datos de demostración.

## Alcance no funcional

- ejecución reproducible mediante Docker;
- configuración por variables de entorno;
- ausencia de secretos en repositorio;
- validación de entradas y salidas;
- logs suficientes para diagnosticar la demo;
- pruebas del flujo crítico;
- interfaz responsive;
- degradación controlada ante errores del modelo o de una herramienta.

## Decisiones de alcance

1. Se usará **acceso demo**, no autenticación completa.
2. Se mostrará **una sola organización ficticia**, no multitenencia.
3. Las comunicaciones permanecerán en **modo borrador**.
4. El CRM, stock y seguimiento serán **simulados pero persistentes**.
5. La demo priorizará un flujo robusto sobre múltiples escenarios.
