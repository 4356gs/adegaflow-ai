# Backlog preliminar

## Convenciones

- **P0:** imprescindible para el MVP demostrable y la validación.
- **P1:** importante si no compromete P0.
- **P2:** posterior a evidencia comercial suficiente.
- **SP:** estimación preliminar relativa; debe revisarse tras la arquitectura.

## Epic E0 — Gobierno y definición

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-001 | Aprobar visión, problema y usuario principal | P0 | 1 | 0 |
| AF-002 | Congelar alcance y exclusiones del MVP | P0 | 1 | 0 |
| AF-003 | Definir caso de uso principal | P0 | 1 | 0 |
| AF-004 | Definir criterios de éxito y riesgos | P0 | 1 | 0 |
| AF-005 | Validar reglas y categoría oficial del hackathon — cerrado históricamente | — | 2 | 1 |

## Epic E1 — Arquitectura y contratos

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-010 | Diseñar arquitectura de contexto y contenedores | P0 | 3 | 1 |
| AF-011 | Definir estructura final del repositorio | P0 | 2 | 1 |
| AF-012 | Definir modelo de datos mínimo | P0 | 3 | 1 |
| AF-013 | Definir contratos API del flujo principal | P0 | 3 | 1 |
| AF-014 | Definir esquemas de entrada/salida de tools | P0 | 3 | 1 |
| AF-015 | Definir estrategia de orquestación | P0 | 3 | 1 |
| AF-016 | Definir estrategia de memoria | P0 | 2 | 1 |
| AF-017 | Definir estrategia de prompts y versionado | P0 | 2 | 1 |
| AF-018 | Redactar ADR-001 a ADR-010 | P0 | 5 | 1 |
| AF-019 | Ejecutar spike de Qwen Cloud y tool calling | P0 | 5 | 1 |

## Epic E2 — Datos de demostración

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-020 | Crear catálogo ficticio verosímil | P0 | 3 | 2 |
| AF-021 | Crear stock y reglas de disponibilidad | P0 | 2 | 2 |
| AF-022 | Crear compradores e historial | P0 | 2 | 2 |
| AF-023 | Crear escenarios de demo y prueba | P0 | 3 | 2 |
| AF-024 | Validar consistencia entre catálogo, stock y precios | P0 | 2 | 2 |

## Epic E3 — Núcleo del agente

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-030 | Integrar Qwen Cloud | P0 | 5 | 2 |
| AF-031 | Implementar extracción estructurada | P0 | 5 | 2 |
| AF-032 | Implementar clasificación y prioridad | P0 | 3 | 2 |
| AF-033 | Implementar orquestador del flujo | P0 | 8 | 2 |
| AF-034 | Implementar validación y reintentos | P0 | 5 | 2 |
| AF-035 | Implementar registro de ejecución | P0 | 3 | 2 |
| AF-036 | Implementar fallback del modelo | P0 | 3 | 2 |

## Epic E4 — Herramientas

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-040 | Implementar `search_catalog` | P0 | 3 | 2 |
| AF-041 | Implementar `check_stock` | P0 | 3 | 2 |
| AF-042 | Implementar `get_product_details` | P0 | 2 | 2 |
| AF-043 | Implementar `calculate_quote` | P0 | 5 | 2 |
| AF-044 | Implementar `retrieve_customer_history` | P0 | 3 | 2 |
| AF-045 | Implementar `save_customer_memory` | P0 | 3 | 2 |
| AF-046 | Implementar `create_crm_opportunity` | P0 | 3 | 2 |
| AF-047 | Implementar `create_followup_task` | P0 | 2 | 2 |
| AF-048 | Implementar `generate_proposal` | P0 | 3 | 2 |
| AF-049 | Implementar `draft_email` | P0 | 3 | 2 |
| AF-050 | Implementar `translate_message` solo si es necesario | P1 | 2 | 2 |

## Epic E5 — Aplicación web

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-060 | Crear acceso demo | P0 | 2 | 3 |
| AF-061 | Crear bandeja de consultas | P0 | 3 | 3 |
| AF-062 | Crear entrada manual y escenario predefinido | P0 | 3 | 3 |
| AF-063 | Mostrar mensaje y datos extraídos | P0 | 3 | 3 |
| AF-064 | Mostrar clasificación y datos faltantes | P0 | 2 | 3 |
| AF-065 | Mostrar herramientas y línea de tiempo | P0 | 5 | 3 |
| AF-066 | Mostrar recomendaciones y stock | P0 | 3 | 3 |
| AF-067 | Mostrar propuesta y borrador | P0 | 5 | 3 |
| AF-068 | Mostrar registro CRM y seguimiento | P0 | 3 | 3 |
| AF-069 | Mostrar memoria recuperada y guardada | P0 | 3 | 3 |
| AF-070 | Añadir panel de métricas simuladas | P2 | 3 | Futuro |
| AF-071 | Exportar propuesta a PDF | P2 | 5 | Futuro |

## Epic E5A — API del flujo principal

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-072 | Crear y consultar inquiries por API | P0 | 3 | 2 |
| AF-073 | Despachar agent runs fuera de la petición HTTP | P0 | 5 | 2 |
| AF-074 | Consultar estado, eventos y resultado por polling | P0 | 5 | 2 |
| AF-075 | Implementar idempotencia de comandos HTTP | P0 | 3 | 2 |
| AF-076 | Recuperar interrupciones y crear retries auditables | P0 | 5 | 2 |
| AF-077 | Publicar read models de oportunidad y memoria | P0 | 3 | 2 |

## Epic E6 — Calidad, seguridad y entrega

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-080 | Pruebas unitarias de tools | P0 | 5 | 2–3 |
| AF-081 | Prueba end-to-end del escenario principal | P0 | 5 | 3 |
| AF-082 | Pruebas de fallos de modelo y tools | P0 | 3 | 3 |
| AF-083 | Configurar Docker y Docker Compose | P0 | 3 | 3 |
| AF-084 | Configurar variables de entorno y secret scanning | P0 | 2 | 3 |
| AF-085 | Preparar README reproducible | P0 | 3 | 3 |
| AF-086 | Preparar guion de demostración comercial | P0 | 3 | 4 |
| AF-087 | Preparar despliegue controlado | P0 | 5 | 4 |
| AF-088 | Preparar capturas y material comercial mínimo | P0 | 3 | 4 |
| AF-089 | Diseñar captura estructurada de feedback | P0 | 3 | 4 |

## Epic E7 — Validación y decisión de inversión

| ID | Historia / tarea | Pri. | SP | Sprint |
|---|---|---:|---:|---:|
| AF-100 | Realizar 5–10 demostraciones con empresas relevantes | P0 | — | Validación |
| AF-101 | Diseñar multitenencia | P2 | — | Futuro |
| AF-102 | Integrar CRM real | P2 | — | Futuro |
| AF-103 | Integrar correo real con aprobación | P2 | — | Futuro |
| AF-104 | Evaluar SaaS y modelo comercial con evidencia | P2 | — | Futuro |
| AF-105 | Evaluar adaptación a otros subsectores | P2 | — | Futuro |
| AF-106 | Registrar reconocimiento del problema y objeciones | P0 | — | Validación |
| AF-107 | Obtener al menos dos segundas conversaciones o interés en piloto | P0 | — | Validación |
| AF-108 | Obtener una conversación sobre precio, datos o condiciones | P0 | — | Validación |
| AF-109 | Decidir continuar, iterar, cambiar segmento o detener | P0 | — | Validación |

## Orden de ejecución recomendado

1. Mantener cerrado el backend de Sprint 2.
2. Aprobar documentación de Sprint 3.
3. Construir la experiencia frontend.
4. Verificar el flujo completo.
5. Preparar despliegue y demostración comercial.
6. Ejecutar validación con empresas relevantes.
7. Decidir inversión con evidencia.

## Política de backlog

Los elementos P1 no comienzan hasta que el escenario principal cumpla todos los criterios P0.
