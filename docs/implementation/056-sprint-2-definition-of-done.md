# Definition of Done del Sprint 2

El Sprint 2 no se considera terminado por tener un endpoint funcional. Debe cumplir todos los puntos.

## Producto

- UC-001 funciona por HTTP.
- Datos extraídos visibles en respuesta API.
- Catálogo y stock provienen de tools.
- Recomendación validada.
- Cotización determinista.
- Propuesta y correo persistidos.
- CRM simulado y seguimiento persistidos.
- Memoria guardada y recuperada.
- Trazabilidad completa.

## Ingeniería

- migración inicial;
- seeds reproducibles;
- schemas tipados;
- errores uniformes;
- idempotencia;
- límites agentic;
- transacciones;
- logs estructurados;
- configuración por entorno;
- Dockerfile funcional;
- sin secretos.

## Pruebas

- unitarias;
- contrato;
- integración;
- end-to-end backend;
- spike live aprobado;
- fallos críticos cubiertos;
- comandos documentados.

## Documentación

- README de backend;
- variables de entorno;
- instrucciones de seeds;
- ejecución local;
- ejecución de tests;
- evidencia del spike;
- OpenAPI accesible;
- ADR-011 vigente.

## Calidad

- Ruff sin errores;
- mypy sin errores bloqueantes;
- tests P0 en verde;
- cobertura objetivo alcanzada o desviación justificada;
- funciones pequeñas;
- nombres de dominio coherentes;
- no existen TODO críticos.

## Revisión

El cierre requiere una demostración desde terminal o Swagger:

1. crear inquiry;
2. iniciar run;
3. consultar eventos;
4. recuperar oportunidad;
5. recuperar memoria;
6. repetir con el mismo comprador.

## Gate hacia Sprint 3

Solo se inicia la aplicación web cuando:

- el contrato API no cambia de forma material;
- AT-001, AT-003, AT-005, AT-007 y AT-009 pasan;
- el backend puede ejecutarse en Docker;
- el flujo no depende de respuestas hardcodeadas.
