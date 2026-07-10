# Riesgos iniciales

## Escala

- **Probabilidad:** Baja / Media / Alta
- **Impacto:** Bajo / Medio / Alto / Crítico

| ID | Riesgo | Prob. | Impacto | Mitigación inicial | Indicador |
|---|---|---:|---:|---|---|
| R-001 | Ampliación continua del alcance | Alta | Crítico | Congelar P0, registrar ideas en backlog y exigir decisión documentada | Nuevas funciones dentro del sprint activo |
| R-002 | Tool calling de Qwen Cloud menos estable de lo esperado | Media | Crítico | Probar un spike temprano, validar esquemas y diseñar fallback | Respuestas no estructuradas o llamadas omitidas |
| R-003 | Salidas del modelo no válidas | Alta | Alto | Pydantic/JSON Schema, reintento controlado y validación determinista | Errores frecuentes de parsing |
| R-004 | Latencia excesiva durante la demo | Media | Alto | Reducir rondas del agente, limitar contexto y precargar datos | Flujo tarda demasiado o parece detenido |
| R-005 | Dependencia de conectividad o API externa | Media | Crítico | Escenario de respaldo, manejo visible de error y demo grabada | Fallos de red o límites de API |
| R-006 | Recomendaciones con stock o precios incoherentes | Media | Crítico | Tools como fuente de verdad; prohibir inventar datos | Discrepancias entre propuesta y catálogo |
| R-007 | Datos de demostración poco creíbles | Media | Alto | Catálogo y compradores coherentes, revisión sectorial posterior | Productos o condiciones genéricas |
| R-008 | El proyecto parece un chatbot | Media | Crítico | UX basada en flujo, herramientas, artefactos y trazabilidad | Demo centrada en una ventana de chat |
| R-009 | Sobreingeniería multiagente | Alta | Alto | Un orquestador con capacidades lógicas salvo necesidad probada | Múltiples servicios sin valor demostrable |
| R-010 | Interfaz consume tiempo del núcleo funcional | Media | Alto | Implementar primero flujo y contratos; UI después | Pantallas avanzadas sin backend estable |
| R-011 | Falta de claridad sobre criterios oficiales del hackathon | Media | Alto | Validar reglas y categorías antes de cerrar Sprint 1 | Narrativa o entrega no alineada |
| R-012 | Mensajes multilingües generan errores de tono o contenido | Media | Medio | Plantillas, pruebas y revisión del borrador | Respuestas correctas semánticamente pero impropias |
| R-013 | Confusión entre datos simulados y hechos reales | Media | Alto | Etiquetas visibles y documentación explícita | Métricas o precios presentados como reales |
| R-014 | Exposición de claves API | Baja | Crítico | Variables de entorno, `.env.example`, secret scanning | Claves en commits o logs |
| R-015 | Ausencia de validación con usuarios del sector | Alta | Alto | Entrevista breve con 1–3 profesionales tras la demo base | Supuestos de proceso no confirmados |
| R-016 | Mezcla accidental con Atlas | Baja | Alto | Repositorio, nombres y documentación separados | Referencias, código o dependencias compartidas |
| R-017 | Preparación tardía de video y submission | Media | Alto | Reservar Sprint 4 y congelar funciones antes | Cambios funcionales durante grabación |
| R-018 | Promesas regulatorias o logísticas excesivas | Media | Alto | Human-in-the-loop y disclaimers | Recomendaciones presentadas como definitivas |

## Riesgos prioritarios del Sprint 1

1. R-002 — compatibilidad real de Qwen Cloud con el patrón de tool calling elegido.
2. R-003 — confiabilidad de salidas estructuradas.
3. R-009 — evitar una arquitectura multiagente innecesaria.
4. R-011 — validar reglas y categoría oficial del hackathon.
5. R-006 — definir una única fuente de verdad para catálogo, stock y precios.

## Regla de gestión

Un riesgo pasa a bloqueo cuando amenaza la ejecución completa del caso de uso principal. Los bloqueos se resuelven antes de añadir funciones P1.
