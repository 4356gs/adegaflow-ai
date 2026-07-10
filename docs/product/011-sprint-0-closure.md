# Cierre del Sprint 0

## Estado

**Sprint 0 completado.**

No se ha iniciado implementación.

## Decisiones tomadas

1. AdegaFlow AI será un producto independiente de Atlas.
2. El producto se posiciona como agente comercial autónomo, no como chatbot.
3. El usuario principal será el responsable comercial o de exportación de una bodega gallega pequeña o mediana.
4. El escenario principal será una consulta en inglés de un distribuidor alemán interesado en 600 botellas de Albariño para tiendas especializadas.
5. El flujo cubrirá análisis, memoria, catálogo, stock, recomendación, propuesta, borrador, CRM y seguimiento.
6. Qwen Cloud será central y visible.
7. Se utilizará una sola bodega ficticia durante la demo.
8. El acceso será modo demo, sin autenticación completa.
9. Catálogo, stock, CRM y seguimiento serán simulados pero coherentes y persistentes.
10. Las comunicaciones permanecerán en borrador.
11. La trazabilidad de decisiones y herramientas será una capacidad P0.
12. El MVP no incluirá multitenencia, integraciones reales ni funciones regulatorias.
13. Los agentes especializados podrán ser roles lógicos; la decisión de implementación se resolverá en arquitectura.
14. Las funciones P1 quedan subordinadas a la estabilidad del flujo P0.

## Decisiones pendientes

| Decisión | Momento de resolución |
|---|---|
| Arquitectura general | ADR-001, Sprint 1 |
| Frontend y organización del monorepo | ADR-002, Sprint 1 |
| Backend y empaquetado Python | ADR-003, Sprint 1 |
| Modelo y API exacta de Qwen Cloud | ADR-004, Sprint 1 |
| Patrón de tool calling | ADR-005, Sprint 1 |
| Memoria de comprador | ADR-006, Sprint 1 |
| SQLite o PostgreSQL | ADR-007, Sprint 1 |
| Estrategia de despliegue | ADR-008, Sprint 1 |
| Logs y trazabilidad técnica | ADR-009, Sprint 1 |
| Separación demo/producto futuro | ADR-010, Sprint 1 |
| Categoría y requisitos oficiales del hackathon | Validación al inicio del Sprint 1 |
| Formato de propuesta: vista HTML o PDF | Sprint 3, sujeto a capacidad |
| Métricas de negocio mostradas | Sprint 3, solo como simulaciones |

## Supuestos

1. Qwen Cloud permite un patrón viable de respuestas estructuradas o tool calling.
2. La demo puede operar con datos ficticios.
3. No es necesario enviar comunicaciones reales.
4. Un único escenario principal es suficiente para demostrar valor, siempre que sea robusto.
5. El usuario acepta revisión humana antes de cualquier acción externa.
6. El catálogo y stock pueden modelarse con un esquema simple.
7. El hackathon valora autonomía, herramientas, ejecución y trazabilidad; debe verificarse contra las reglas oficiales.
8. El producto no necesita multitenencia para competir.
9. La recomendación comercial puede basarse en reglas y contexto de demostración sin ofrecer asesoramiento regulatorio.
10. La persistencia local es aceptable para la primera demo, sujeto a ADR.

## Cuestiones abiertas de producto

- ¿Qué señales exactas determinan prioridad alta, media o baja?
- ¿Qué campos mínimos debe contener una propuesta?
- ¿Cómo se representan cajas, botellas y combinaciones de referencias?
- ¿Qué información del comprador debe persistirse como memoria?
- ¿Qué grado de edición manual se permite antes de ejecutar el flujo?
- ¿Qué métricas son útiles sin presentar cifras no validadas?
- ¿Qué información sectorial debe revisarse con una bodega real?

## Siguiente documento recomendado

`docs/architecture/020-architecture-overview.md`

Debe contener:

- contexto del sistema;
- contenedores;
- componentes;
- flujo de datos;
- límites entre IA y lógica determinista;
- estrategia preliminar de fallos;
- alternativas evaluadas;
- decisiones que requieren ADR.

Después deben redactarse ADR-001 a ADR-010 antes de programar.

## Criterio de entrada al Sprint 1

El Sprint 1 puede comenzar porque:

- el producto está definido;
- el alcance P0 está congelado;
- el escenario de demo está cerrado;
- los riesgos críticos están identificados;
- el backlog preliminar existe;
- las decisiones técnicas pendientes están explicitadas.
