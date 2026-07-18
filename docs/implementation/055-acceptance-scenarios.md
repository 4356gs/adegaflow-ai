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

## AT-013 — Acciones internas completas

Quote, propuesta y correo son válidos y pertenecen al mismo run.

**Esperado:** crear oportunidad con score y prioridad deterministas, seguimiento
a siete días y memoria explícita; registrar las tres tools y terminar
`needs_review` sin otra llamada a Qwen.

## AT-014 — Artefactos parciales

Existe quote, pero falta propuesta o correo válido.

**Esperado:** conservar el resultado parcial en `needs_review`; no ejecutar
oportunidad, seguimiento ni memoria.

## AT-011 — Límite de rondas

El modelo continúa solicitando tools.

**Esperado:** detener al alcanzar el límite y marcar `needs_review` o `failed` según resultados.

## AT-012 — Ausencia de clave API

La API arranca en modo test, pero una ejecución live no puede iniciarse.

**Esperado:** health informa `qwen_configured=false`; no expone configuración sensible.
