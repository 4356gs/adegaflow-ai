# Definition of Done del Sprint 2

El Sprint 2 no se considera terminado por tener un endpoint funcional. Debe cumplir todos los puntos.

## Producto

- UC-001 funciona por HTTP.
- Los comandos HTTP son idempotentes.
- El procesamiento ocurre fuera de la petición original.
- Datos extraídos visibles en respuesta API.
- Catálogo y stock provienen de tools.
- Recomendación validada.
- Cotización determinista.
- Propuesta y correo persistidos.
- CRM simulado y seguimiento persistidos.
- Memoria guardada y recuperada.
- Acciones internas atómicas e idempotentes.
- Trazabilidad completa.
- Estado, eventos y resultado son consultables mediante polling.
- Los fallos recuperables pueden crear un nuevo intento auditable.

## Ingeniería

- migración inicial;
- seeds reproducibles;
- schemas tipados;
- errores uniformes;
- idempotencia;
- claves HTTP persistentes;
- receipts y fingerprints para escrituras internas;
- límites agentic;
- transacciones;
- logs estructurados;
- dispatcher local con un solo consumidor;
- recuperación segura de runs interrumpidos;
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
- rutas de producto exclusivamente bajo `/api/v1`;
- limitación de un worker documentada;
- ADR-011 vigente.
- ADR-014 vigente.

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

La demostración HTTP debe probar además:

7. respuesta `202` al iniciar el run;
8. polling de estado y eventos;
9. resultado expandido terminal;
10. idempotencia de un POST repetido;
11. retry de un fallo recuperable mediante un run nuevo.

La demostración debe mostrar además que repetir las acciones del mismo run no
duplica oportunidad, seguimiento ni memoria.

## Gate hacia Sprint 3

Solo se inicia la aplicación web cuando:

- el contrato API no cambia de forma material;
- AT-001, AT-003, AT-004, AT-005, AT-007, AT-008, AT-009, AT-010, AT-013 y
  AT-014, AT-015, AT-016, AT-017, AT-018, AT-019 y AT-020 pasan;
- el backend puede ejecutarse en Docker;
- el flujo no depende de respuestas hardcodeadas.
- el contrato OpenAPI no publica rutas de producto sin versión;
- no se necesita una cola durable para ejecutar la demo con un worker.
