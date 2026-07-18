# Escenarios de aceptación del Sprint 2

## AT-001 — Camino feliz UC-001

**Dado** el mensaje del distribuidor alemán  
**Cuando** se ejecuta el agente  
**Entonces**:

- extrae los datos esperados;
- recupera memoria;
- consulta catálogo y stock;
- selecciona dos referencias disponibles;
- cotiza 600 botellas;
- crea propuesta en inglés;
- crea borrador en inglés;
- registra oportunidad;
- programa seguimiento a siete días;
- guarda memoria;
- finaliza `needs_review` o `completed`;
- registra las tools.

## AT-002 — Datos faltantes

La consulta no incluye presupuesto ni dirección de muestras.

**Esperado:** campos faltantes visibles; el agente no inventa datos; la propuesta muestra supuestos.

## AT-003 — Stock insuficiente

Se solicitan 900 botellas de un producto con 720 disponibles.

**Esperado:** no cotizar 900 como disponibles; proponer alternativa o marcar necesidad de revisión.

## AT-004 — Comprador desconocido

No existe customer.

**Esperado:** si el análisis validado contiene empresa y mercado, crear perfil
mínimo, asociar inquiry y guardar memoria inicial dentro de la misma
transacción. Si falta cualquiera de esos dos campos, no crear un placeholder y
terminar `needs_review`.

## AT-005 — JSON inválido

El cliente Qwen falso devuelve contenido no conforme.

**Esperado:** intento de reparación; si falla, run `failed` con `MODEL_INVALID_JSON`.

## AT-006 — Tool inexistente

El modelo solicita una tool fuera de la allowlist.

**Esperado:** rechazo, evento de error y corrección controlada; no ejecutar código arbitrario.

## AT-007 — Timeout

Qwen excede timeout.

**Esperado:** reintentos limitados; run consistente; error seguro; endpoint de retry disponible.

## AT-008 — Idempotencia

Se repite una escritura con la misma idempotency key.

**Esperado:** la misma clave y fingerprint reutiliza las referencias sin
duplicar oportunidad, seguimiento ni memoria. La misma clave con otro
fingerprint produce `IDEMPOTENCY_CONFLICT` y no sobrescribe datos.

## AT-009 — Segunda sesión

Se procesa una nueva consulta del mismo comprador.

**Esperado:** recuperar preferencias guardadas y mostrarlas en la ejecución.

## AT-010 — Error de persistencia

Una escritura falla dentro de la transacción.

**Esperado:** rollback de customer nuevo, asociación, oportunidad, seguimiento,
memorias y receipts; se conservan quote y artefactos del Bloque 6 y no quedan
registros parciales incompatibles.

## AT-011 — Límite de rondas

El modelo continúa solicitando tools.

**Esperado:** detener al alcanzar el límite y marcar `needs_review` o `failed` según resultados.

## AT-012 — Ausencia de clave API

La API arranca en modo test, pero una ejecución live no puede iniciarse.

**Esperado:** health informa `qwen_configured=false`; no expone configuración sensible.

## AT-013 — Acciones internas completas

Quote, propuesta y correo son válidos y pertenecen al mismo run.

**Esperado:** crear oportunidad con score y prioridad deterministas, seguimiento
a siete días y memoria explícita; registrar las tres tools y terminar
`needs_review` sin otra llamada a Qwen.

## AT-014 — Artefactos parciales

Existe quote, pero falta propuesta o correo válido.

**Esperado:** conservar el resultado parcial en `needs_review`; no ejecutar
oportunidad, seguimiento ni memoria.

## AT-015 — Ejecución HTTP asíncrona

**Dado** que existe una inquiry válida

**Cuando** se crea un run mediante `POST /api/v1/inquiries/{id}/agent-runs`

**Entonces** responde `202` después de persistir `queued`, encola una sola vez y
el cliente puede observar la transición mediante polling sin mantener abierta
la petición original.

## AT-016 — Idempotencia HTTP

**Dado** un comando POST con `Idempotency-Key`

**Cuando** el cliente repite el mismo comando

**Entonces** recibe el mismo recurso y no duplica inquiry, run ni enqueue. Si
reutiliza la clave con otro contenido o parent, recibe
`IDEMPOTENCY_CONFLICT`.

## AT-017 — Interrupción del proceso

**Dado** un run `queued` o `running` que pertenecía al proceso anterior

**Cuando** FastAPI inicia de nuevo

**Entonces** el run termina `failed` con `RUN_INTERRUPTED`, conserva auditoría y
se marca retryable sin reanudar automáticamente Qwen.

## AT-018 — Retry auditable

**Dado** un run terminal con error recuperable

**Cuando** se solicita retry con una clave nueva

**Entonces** se crea otro run para la misma inquiry, se conserva
`retry_of_run_id`, el intento original permanece inmutable y el nuevo run se
encola una vez. Un run exitoso que espera revisión humana no admite retry.

## AT-019 — Resultado HTTP completo

**Dado** un run terminal

**Cuando** se consulta su resultado

**Entonces** la API ensambla desde fuentes autoritativas las secciones
disponibles de análisis, recomendación, quote, artefactos y acciones, sin
exponer secretos, datos sensibles innecesarios o respuestas crudas de Qwen.

## AT-020 — Versionado de rutas

**Esperado:** `/health` permanece sin versión; inquiries, runs, oportunidades y
memoria solo están disponibles bajo `/api/v1`. No existe un alias accidental
`/inquiries`.
