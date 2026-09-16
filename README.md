# GovTracker RD

Plataforma de inteligencia sobre la contratación pública de República Dominicana.
Ingiere los datos abiertos del Estado, los normaliza en un modelo relacional y
cruza contratos, empresas y funcionarios para hacer visibles patrones que en las
fuentes originales quedan dispersos entre portales.

> **Los datos son públicos; el aporte es el cruce.** Un contrato aislado no dice
> nada. El mismo proveedor apareciendo en tres instituciones, con un socio que
> figura en la nómina de una de ellas, sí.

## Qué resuelve

Los portales oficiales publican contratos, nóminas y registros mercantiles en
sitios distintos, con formatos distintos y sin identificadores comunes. Responder
"¿qué empresas concentran las compras de esta institución y quién está detrás?"
exige cruzar a mano miles de registros. GovTracker automatiza ese cruce.

## Capacidades

- **ETL de fuentes públicas** — pipeline de ingesta con scraping (Playwright,
  BeautifulSoup) y normalización a un esquema común.
- **Detección de patrones** — reglas que marcan señales para revisión humana:
  concentración de adjudicaciones en un proveedor, doble cobro en nómina,
  proveedores inhabilitados con contratos vigentes.
- **Grafo de relaciones** — visualización de vínculos entre empresas,
  instituciones y personas (`react-force-graph`).
- **Alertas y digest** — escaneo periódico con diff contra el estado anterior,
  para notificar solo lo que cambió.
- **Fichas navegables** — contratos, empresas, instituciones, legisladores,
  comisiones y gasto ejecutado.

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI · SQLAlchemy 2 · Pydantic v2 · Alembic |
| Datos | PostgreSQL (asyncpg) · SQLite en desarrollo |
| ETL | Playwright · BeautifulSoup · httpx / aiohttp |
| Frontend | React · TypeScript · TanStack Table · Recharts · Tailwind |
| Despliegue | Docker · nginx |

## Arquitectura

```
backend/app/
  api/routes/   endpoints REST
  models/       modelo relacional (SQLAlchemy)
  schemas/      contratos de entrada/salida (Pydantic)
  etl/          ingesta y normalización por fuente
  services/     reglas de detección, alertas, investigación
frontend/src/
  pages/        fichas y paneles
  components/   UI compartida
```

## Tests

`backend/tests/` cubre las reglas de detección y el pipeline: `test_alert_diff`,
`test_alert_scanner_empresa_concentrada`, `test_nomina_doble_cobro`,
`test_dgii_cedula_backfill`, `test_pipeline_sources`, `test_orchestrator`.

```bash
cd backend && pytest
```

## Nota sobre los datos

Todo procede de fuentes oficiales de acceso público. El sistema **no emite
acusaciones**: marca patrones estadísticos que requieren verificación humana.
Una señal es un punto de partida para investigar, no una conclusión.

## Licencia

Propietario — todos los derechos reservados. Visible para evaluación técnica;
no se autoriza su uso, copia ni distribución. Ver [LICENSE](LICENSE).
