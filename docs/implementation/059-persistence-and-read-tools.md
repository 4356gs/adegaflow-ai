# Implementación de persistencia y tools de lectura

## Estado

- **Sprint:** 2 — Núcleo funcional
- **Bloques:** 2 y 3
- **Fecha:** 2026-07-11
- **Estado:** Implementado; pendiente verificación combinada en WSL y Docker

## Alcance implementado

### Persistencia

- SQLite como base MVP;
- SQLAlchemy 2.0 síncrono;
- Alembic con migración inicial;
- sesiones transaccionales;
- foreign keys habilitadas en SQLite;
- repositorios desacoplados de FastAPI y Qwen;
- un solo worker en la imagen Docker.

### Entidades del bloque

- `products`;
- `inventory`;
- `customers`;
- `inquiries`;
- `customer_memories`;
- `opportunities`.

No se adelantaron cotizaciones, artefactos, seguimientos, agent runs ni tool executions. Esas tablas entran cuando exista un consumidor funcional en los bloques posteriores.

## Corrección de contrato

`search_catalog` ya aceptaba el filtro `channel`, pero el modelo canónico de producto solo registraba mercados recomendados. Se añadió:

```text
recommended_channels: JSON
```

Es una corrección de consistencia entre dos documentos aprobados, no una ampliación del producto.

## Datos demo

El archivo `data/seeds/demo_seed.json` contiene:

- seis referencias ficticias;
- inventario con stock vendible documentado;
- dos compradores ficticios;
- memorias activas e inactivadas;
- una consulta y una oportunidad históricas;
- UUID fijos;
- versión de seed explícita.

El loader es idempotente mediante claves primarias fijas. `--reset` elimina las tablas demo actuales y restaura los valores canónicos; por tanto, es una operación destructiva limitada al MVP.

## Tools implementadas

### `search_catalog`

Filtra productos activos por:

- texto;
- mercado;
- canal;
- precio máximo;
- límite.

La clasificación es determinista y devuelve razones de coincidencia. No contiene la recomendación 360/240 hardcodeada.

### `get_product_details`

Devuelve fichas completas en el orden solicitado, excluye inventario e identifica IDs no encontrados.

### `check_stock`

Calcula:

```text
sellable_bottles = max(0, available_bottles - reserved_bottles)
shortfall = max(0, requested_bottles - sellable_bottles)
```

No reserva ni modifica stock.

### `retrieve_customer_history`

Devuelve:

- ficha del comprador;
- memorias activas;
- filtro opcional por categoría;
- oportunidades anteriores resumidas;
- orden cronológico descendente.

## Manejo de errores

Las tools utilizan el envelope común aprobado y no exponen excepciones de SQLAlchemy. Los errores actuales son:

- `NOT_FOUND`;
- `PERSISTENCE_ERROR`.

La validación de argumentos ocurre mediante Pydantic antes de ejecutar repositorios.

## Pruebas incorporadas

- upgrade y downgrade de la migración;
- carga idempotente del seed;
- restauración con reset;
- búsqueda y ranking del catálogo;
- filtro de precio;
- detalles sin stock;
- stock suficiente;
- stock insuficiente de 900 botellas sobre lías;
- producto inexistente;
- rechazo de productos duplicados en una consulta de stock;
- recuperación de memoria activa;
- filtro de memoria;
- comprador inexistente.

## Comandos

```bash
make db-upgrade
make seed-demo
make seed-demo-reset
make check-api
```

## Riesgos restantes

1. SQLite sigue limitado a una instancia y un worker.
2. El reset del seed no debe utilizarse con datos reales.
3. Las tools todavía no se registran en el ciclo agentic; eso corresponde al bloque de orquestación.
4. La imagen Docker y el volumen persistente deben verificarse en el entorno Docker del usuario.

## Siguiente bloque autorizado

Análisis estructurado de consultas mediante `inquiry_analysis.v1`, sin iniciar frontend ni orquestador completo.
