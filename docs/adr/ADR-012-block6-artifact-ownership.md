# ADR-012: Propiedad de cotizaciones y artefactos antes de crear la oportunidad

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-13
- **Decisores:** Equipo técnico AdegaFlow AI
- **Relacionados:** ADR-003, ADR-005, ADR-007, ADR-009

## Contexto

El Sprint 2 Bloque 6 debe calcular una cotización y persistir una propuesta y un borrador de correo. La creación de la oportunidad CRM pertenece al Bloque 7.

El modelo de datos anterior vinculaba `quotes` y `generated_artifacts` de forma obligatoria a `opportunities`. Los contratos anteriores de `generate_proposal` y `draft_email` también exigían `opportunity_id`.

Aplicar esos contratos literalmente obligaría a:

- crear una oportunidad antes del Bloque 7;
- utilizar un identificador inexistente;
- o introducir una entidad intermedia adicional.

Las tres opciones debilitan la secuencia del Sprint o amplían el alcance sin valor demostrable.

## Decisión

1. `quotes.agent_run_id` será obligatorio y único.
2. `quotes` no almacenará `opportunity_id` ni `inquiry_id`. La inquiry se obtiene de forma inequívoca mediante `agent_run.inquiry_id`.
3. `generated_artifacts.agent_run_id` y `generated_artifacts.quote_id` serán obligatorios.
4. `generated_artifacts` no almacenará `opportunity_id`. La oportunidad futura se obtiene mediante la relación `artifact -> quote -> agent_run -> inquiry` y el `opportunities.inquiry_id` único.
5. Existirá como máximo un artefacto de cada tipo por run mediante `unique(agent_run_id, artifact_type)`.
6. El Bloque 7 creará la oportunidad asociada a la misma inquiry sin actualizar ni rellenar claves foráneas en cotizaciones o artefactos.
7. `calculate_quote` será una capacidad determinista de aplicación invocada por el orquestador. No se expondrá a Qwen dentro del tool registry.
8. Qwen generará solo narrativa. Los importes, cantidades, productos, cajas, moneda y supuestos comerciales serán ensamblados por el backend desde datos verificados.
9. No se creará una entidad `commercial_package` ni equivalente en el MVP.

## Alternativas consideradas

### Crear la oportunidad en el Bloque 6

Descartada porque adelanta una acción CRM expresamente planificada para el Bloque 7 y mezcla generación de artefactos con persistencia comercial interna.

### Mantener `opportunity_id` obligatorio y usar un placeholder

Descartada porque viola integridad referencial y genera estados imposibles de auditar.

### Crear una entidad `commercial_package`

Podría agrupar recomendación, cotización y artefactos, pero añade otro agregado, repositorio, migración y ciclo de vida sin necesidad para el camino feliz del hackathon.

### Persistir todo dentro de `agent_runs.result_payload`

Descartada para cotizaciones y artefactos porque estos ya poseen identidad, estado de revisión y relaciones propias. Mantenerlos como entidades separadas evita sobrescribir snapshots comerciales.

## Consecuencias

### Positivas

- conserva la secuencia Bloque 6 antes de Bloque 7;
- evita identificadores ficticios y claves foráneas nullable;
- mantiene trazabilidad por run;
- permite obtener la oportunidad futura mediante la inquiry compartida;
- evita backfills y duplicados en reintentos;
- mantiene la aritmética fuera del modelo;
- no introduce agregados innecesarios.

### Negativas

- las consultas por oportunidad requieren un join adicional mediante `agent_runs` e `inquiries`;
- la relación comercial no queda materializada directamente en cotizaciones o artefactos.

### Riesgos

- reintentos que intenten crear más de una cotización por run;
- artefactos parciales si Qwen falla después de persistir la cotización;
- divergencia entre el snapshot cotizado y cambios posteriores del catálogo.

## Mitigación

- restricción única por `agent_run_id`;
- restricción única por run y tipo de artefacto;
- relación derivable mediante claves foráneas existentes e `opportunities.inquiry_id` único;
- persistencia por fases con commits independientes;
- terminal `needs_review` para resultados parciales útiles;
- precios snapshot provenientes de la recomendación validada;
- no reservar stock ni prometer vigencia automática.

## Condición de revisión

Revisar esta decisión si:

- el producto requiere varias cotizaciones por run;
- se introduce versionado o negociación de propuestas;
- una oportunidad puede agrupar múltiples inquiries;
- se implementan envíos reales, aprobación formal o firma;
- el flujo comercial deja de ser secuencial.
