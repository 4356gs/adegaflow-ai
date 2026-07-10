# Sprint 2 — Charter del núcleo funcional

## Estado

- **Sprint:** 2 — Núcleo funcional
- **Estado actual:** Ready for implementation
- **Documentación:** Completada
- **Código de producto:** No iniciado
- **Objetivo único:** implementar y probar el flujo backend UC-001 desde la consulta hasta la generación de resultados persistidos.

## Resultado esperado

Una API ejecutable que:

1. reciba la consulta del importador;
2. la analice con Qwen Cloud;
3. recupere memoria del comprador;
4. consulte catálogo y stock mediante tools;
5. recomiende productos válidos;
6. calcule una cotización;
7. genere propuesta y borrador;
8. cree oportunidad y seguimiento;
9. guarde memoria;
10. exponga trazabilidad completa.

No se construirá la interfaz final durante este sprint.

## Alcance P0

- estructura inicial del repositorio;
- configuración de FastAPI;
- configuración de SQLAlchemy y Alembic;
- cliente Qwen;
- schemas Pydantic;
- prompts versionados;
- datos semilla;
- tools P0;
- orquestador;
- endpoints backend P0;
- persistencia;
- logs y eventos;
- pruebas unitarias, de integración y end-to-end del backend;
- Dockerfile de API;
- `.env.example`;
- documentación de ejecución local.

## Fuera del Sprint 2

- frontend Next.js completo;
- despliegue definitivo en ECS;
- PDF;
- correo real;
- CRM real;
- multitenencia;
- autenticación;
- dashboards;
- streaming de tokens;
- Responses API como dependencia;
- herramientas integradas de búsqueda web;
- MCP;
- vector database;
- múltiples agentes.

## Gate de inicio

No se implementa el orquestador hasta superar el spike:

- llamada simple;
- salida JSON;
- una llamada de tool;
- devolución del resultado de tool;
- respuesta final;
- timeout y error controlados.

## Criterios de aceptación del sprint

- UC-001 completa el flujo mediante API.
- Qwen Cloud participa de forma real.
- Se ejecutan al menos catálogo, stock y una tool de escritura interna.
- La cotización es determinista.
- No se recomienda stock insuficiente.
- Las acciones son persistentes.
- La memoria se recupera en una segunda ejecución.
- El run registra tools, duración y estado.
- Los fallos críticos tienen respuesta controlada.
- Las pruebas se ejecutan en un comando documentado.

## Restricción

Una funcionalidad nueva solo entra si corrige un fallo de UC-001. Todo lo demás pasa al backlog.
