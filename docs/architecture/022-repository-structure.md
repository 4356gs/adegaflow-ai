# Estructura del repositorio

## Decisión

Se utilizará un monorepo sin una capa `packages/` prematura. Los componentes compartidos se mantendrán dentro de la aplicación que los ejecuta y los contratos públicos se publicarán mediante OpenAPI y documentación.

```text
adegaflow-ai/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── public/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── next.config.*
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   │   └── v1/
│       │   ├── agent/
│       │   │   ├── orchestrator.py
│       │   │   ├── policies.py
│       │   │   ├── state.py
│       │   │   └── tools/
│       │   ├── ai/
│       │   │   ├── qwen_client.py
│       │   │   ├── schemas.py
│       │   │   └── prompts/
│       │   ├── core/
│       │   ├── domain/
│       │   ├── repositories/
│       │   ├── services/
│       │   ├── db/
│       │   └── main.py
│       ├── alembic/
│       ├── tests/
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── alembic.ini
├── data/
│   ├── catalog/
│   ├── customers/
│   ├── demo-scenarios/
│   └── seeds/
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── adr/
│   ├── hackathon/
│   └── commercial/
├── infra/
│   ├── alibaba-cloud/
│   └── docker/
├── scripts/
├── tests/
│   └── e2e/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
└── README.md
```

## Motivos del ajuste frente a la estructura inicial

La estructura preliminar proponía `packages/agent-core`, `packages/tools`, `packages/prompts` y `packages/shared`. Esa separación se descarta para el MVP porque:

- crea fronteras de paquete sin consumidores independientes;
- complica imports, empaquetado y Docker;
- no aporta despliegues separados;
- aumenta el tiempo de configuración.

Los módulos podrán extraerse cuando exista una segunda aplicación o un caso real de reutilización.

## Reglas de dependencia

```text
api routes
  → application services
    → domain / agent orchestration
      → repository interfaces / tool interfaces
        → infrastructure adapters
```

- `domain` no importa FastAPI.
- `agent` no accede directamente a SQL.
- `tools` utilizan servicios o repositorios tipados.
- `qwen_client` queda detrás de una interfaz.
- `web` nunca accede directamente a SQLite o Qwen Cloud.
- los datos semilla se cargan mediante scripts, no mediante lógica hardcodeada en el agente.

## Convenciones

- Python: `snake_case`.
- TypeScript: `camelCase`; componentes en `PascalCase`.
- IDs: UUID en la API; se almacenan como texto en SQLite.
- Fechas: UTC en backend, ISO 8601 en API.
- Dinero: enteros en céntimos o `Decimal`, nunca `float`.
- Versionado API: `/api/v1`.
- Prompts: archivos versionados, por ejemplo `inquiry_analysis.v1.md`.
