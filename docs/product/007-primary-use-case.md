# Caso de uso principal

## UC-001 — Gestionar una consulta de un importador alemán

### Objetivo

Transformar una consulta comercial en inglés en una oportunidad B2B cualificada, una recomendación de productos, una propuesta, un borrador de respuesta, un registro CRM y una tarea de seguimiento.

### Actor principal

Responsable comercial o de exportación de la bodega.

### Actor externo

Importador o distribuidor alemán.

### Disparador

El responsable comercial recibe o introduce el siguiente tipo de mensaje:

> A German distributor is evaluating Galician Albariño for specialised wine shops. They estimate an initial order of 600 bottles within 60 days and request a price list and samples.

### Datos conocidos

- mercado: Alemania;
- volumen estimado: 600 botellas;
- interés: Albariño;
- canal: tiendas especializadas;
- fecha objetivo: 60 días;
- solicitud: lista de precios y muestras;
- idioma: inglés.

### Datos potencialmente faltantes

- presupuesto;
- ciudad o región de distribución;
- formato de cajas;
- dirección para muestras;
- condiciones de entrega;
- certificaciones requeridas;
- datos fiscales;
- fecha exacta de decisión.

### Precondiciones

- catálogo de demostración cargado;
- stock disponible;
- comprador existente o identificable;
- herramientas simuladas operativas;
- Qwen Cloud configurado;
- usuario en modo demo.

## Flujo principal

1. El usuario abre la consulta.
2. El sistema conserva y muestra el mensaje original.
3. Qwen Cloud detecta idioma, intención y tipo de oportunidad.
4. El agente extrae los datos estructurados.
5. El agente identifica la información faltante.
6. El agente recupera el historial del comprador.
7. El agente consulta el catálogo.
8. El agente consulta stock de los productos candidatos.
9. El agente selecciona dos referencias compatibles con mercado, canal, volumen y disponibilidad.
10. El agente genera una justificación comercial.
11. El agente calcula una propuesta preliminar.
12. El agente genera un documento o vista de propuesta.
13. El agente redacta una respuesta en inglés.
14. El agente crea una oportunidad en el CRM simulado.
15. El agente crea una tarea de seguimiento para siete días después.
16. El agente guarda las preferencias detectadas.
17. La interfaz muestra el resultado y la trazabilidad completa.
18. El usuario revisa y aprueba conceptualmente el borrador; no se envía nada.

## Resultado esperado

- oportunidad clasificada como B2B internacional;
- prioridad asignada;
- dos productos recomendados y disponibles;
- propuesta coherente con 600 botellas;
- borrador en inglés;
- oportunidad registrada;
- seguimiento a siete días;
- memoria actualizada;
- acciones visibles.

## Flujos alternativos

### A1 — Stock insuficiente

El agente no recomienda un producto sin disponibilidad. Propone una combinación alternativa, reduce la cantidad o marca la necesidad de validación.

### A2 — Comprador desconocido

El agente crea un perfil básico con la información disponible y señala los datos pendientes.

### A3 — Datos insuficientes para cotizar

El agente genera una respuesta de clarificación y registra la oportunidad sin inventar precios ni condiciones.

### A4 — Error de una herramienta

La acción queda marcada como fallida, el flujo no oculta el error y el usuario recibe una recomendación de recuperación.

### A5 — Salida inválida del modelo

El backend valida la estructura, solicita una corrección controlada o aplica una ruta de fallback.

## Reglas de negocio iniciales

- no recomendar productos sin stock confirmado;
- no inventar certificaciones;
- los precios son preliminares y de demostración;
- las condiciones logísticas requieren validación humana;
- la comunicación no se envía automáticamente;
- el seguimiento estándar del escenario es de siete días;
- toda acción debe quedar registrada.

## Criterios de aceptación

- el flujo se completa desde el mensaje hasta el seguimiento;
- se utilizan al menos tres herramientas;
- la recomendación solo incluye productos válidos;
- los campos extraídos son visibles y editables en una fase posterior;
- la respuesta está en inglés;
- no existe ninguna acción externa irreversible.
