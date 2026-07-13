# Estrategia de prompts

## Objetivo

Obtener resultados consistentes, auditables y fáciles de probar sin concentrar todo el comportamiento en un prompt monolítico.

## Prompts versionados

```text
apps/api/app/ai/prompts/
├── system_policy.v1.md
├── inquiry_analysis.v1.md
├── tool_selection.v1.md
├── product_recommendation.v1.md
├── proposal_writer.v1.md
└── email_writer.v1.md
```

## Separación de responsabilidades

### `system_policy`

- identidad del agente;
- prohibición de inventar precio, stock, certificación o condiciones;
- obligación de utilizar tools;
- idiomas;
- revisión humana;
- límites de seguridad.

### `inquiry_analysis`

- esquema JSON;
- definición de campos;
- clasificación;
- faltantes;
- señales de prioridad.

### `tool_selection`

- objetivo de la fase;
- tools disponibles;
- criterios de parada;
- restricciones de uso.

### `product_recommendation`

- contexto del comprador;
- productos y stock verificados;
- criterios comerciales;
- formato de recomendación.

### `proposal_writer`

- datos verificados;
- estructura;
- supuestos;
- exclusiones regulatorias.

### `email_writer`

- idioma;
- tono;
- resumen;
- preguntas faltantes;
- llamada a la acción;
- prohibición de afirmar envío o aprobación.

## Política de artefactos del Bloque 6

- Qwen genera narrativa, no importes vinculantes;
- el backend ensambla productos, cantidades, precios, subtotal y moneda;
- `proposal_writer.v1` y `email_writer.v1` usan schemas Pydantic distintos;
- cada prompt permite un intento inicial y una reparación;
- no se utilizan tools durante la redacción;
- ambos artefactos quedan `needs_review`;
- no se afirma envío, aprobación ni reserva de stock.

## Formato

- análisis estructurado mediante JSON mode cuando el modelo lo soporte;
- salidas validadas con Pydantic;
- temperatura baja para extracción y herramientas;
- temperatura moderada para redacción;
- modelos y parámetros configurables por variables de entorno.

## Política de contexto

Se incluirá solo:

- mensaje original;
- datos estructurados actuales;
- memoria relevante;
- resultados de tools;
- reglas aplicables;
- versión de prompt.

No se enviará:

- base de datos completa;
- logs técnicos;
- memorias irrelevantes;
- secretos;
- cadena de pensamiento previa.

## Control de calidad

Cada prompt tendrá:

- objetivo;
- entradas;
- salida esperada;
- ejemplos mínimos;
- casos de prueba;
- versión;
- changelog cuando cambie comportamiento.

## Estrategia de modelos

Baseline:

- modelo principal configurable, inicialmente `qwen3.7-plus`;
- modelo económico de respaldo para reparación de JSON o tareas simples, inicialmente `qwen3.6-flash`;
- `QWEN_MODEL` y `QWEN_FALLBACK_MODEL` por entorno.

La selección definitiva se confirma en el spike del Sprint 2. No se acoplará el dominio a un identificador fijo.

## Thinking mode

No será requisito del MVP.

Motivos:

- JSON mode y flujos deterministas son más predecibles en modo no-thinking;
- la latencia es relevante en la demo;
- no se necesita exponer razonamiento;
- el valor debe demostrarse mediante tools y resultados, no mediante texto de razonamiento.

Podrá probarse fuera del camino crítico si mejora de forma medible la selección de herramientas.
