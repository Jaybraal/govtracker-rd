# Investigador Autónomo GovTracker RD — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir GovTracker RD en un investigador autónomo: motor de detección versionado en git, corrida diaria automática en GitHub Actions, avisos por Telegram, y las tres reglas de alerta más ruidosas auditadas y corregidas con datos reales (no umbrales adivinados).

**Architecture:** Un nuevo módulo `app/etl/orchestrator.py` corre las 5 fuentes de cadencia diaria registrando `EtlRun` por cada una (un fallo no aborta las demás). `app/services/alert_diff.py` aísla lo nuevo desde la última corrida. `app/services/digest.py` lo formatea. `app/services/notifier.py` lo envía — hoy solo Telegram; Gmail queda con código real pero sin credenciales (se activa solo poniendo el secreto, sin tocar código). `scripts/investigar.py` ensambla todo y es el entrypoint que llama el cron de GitHub Actions, que cachea la BD sqlite de 320MB entre corridas.

**Tech Stack:** Python 3.11, FastAPI/SQLAlchemy (ya en el proyecto), pytest (nuevo), GitHub Actions, httpx (ya en el proyecto) para Telegram, smtplib (stdlib) para Gmail.

## Global Constraints

- Motor: la BD de desarrollo es **sqlite** (`backend/.env` → `DATABASE_URL=sqlite:///./govtracker_test.db`), no Postgres — todo el código nuevo debe funcionar contra sqlite, que es lo que correrá en CI.
- Ningún secreto entra al repo. `backend/.env` sigue ignorado; todo secreto se inyecta por variable de entorno (local) o `env:`/`secrets:` (Actions).
- No fabricar datos ni umbrales a ciegas — cada número de configuración en este plan viene de una consulta real contra `govtracker_test.db`, documentada en el paso donde se usa.
- Repo objetivo: **privado**. Nombre: `govtracker-rd`.
- Gmail queda **fuera de esta ejecución** (decisión del usuario, 15/07/26): el código de `GmailNotifier` se escribe completo y correcto, pero no se conecta ningún secreto real ni se prueba envío. Se activa después sin tocar código, solo agregando `GMAIL_USER`/`GMAIL_APP_PASSWORD`/`ALERT_EMAIL_TO`.
- Fuera de alcance de este plan (quedan para una ejecución posterior, ver spec §3.4/§4/§5): reglas nuevas de cruce (`IMPUTADO_CONTRATISTA`, `GASTO_SIN_CONTRATO`, `REPRESENTANTE_MULTI_EMPRESA`), reactivar fuentes congeladas (bancos/JCE/cooperativas), y materializar `intelligence.py`.

---

## File Structure

**Nuevos:**
- `backend/app/etl/orchestrator.py` — corre las 5 fuentes diarias, registra `EtlRun`, tolera fallos individuales.
- `backend/app/services/alert_diff.py` — alertas nuevas desde una fecha.
- `backend/app/services/digest.py` — formatea alertas en texto plano agrupado por severidad.
- `backend/app/services/notifier.py` — `TelegramNotifier`, `GmailNotifier`, `get_notifiers()`.
- `backend/scripts/__init__.py`, `backend/scripts/investigar.py` — entrypoint del cron.
- `backend/tests/__init__.py`, `backend/tests/conftest.py` — fixture de sqlite en memoria.
- `backend/tests/test_orchestrator.py`, `test_alert_diff.py`, `test_digest.py`, `test_notifier.py`, `test_investigar.py`, `test_dgii_cedula_backfill.py`, `test_nomina_doble_cobro.py`, `test_alert_scanner_empresa_concentrada.py`.
- `.github/workflows/investigar.yml` — cron diario.

**Modificados:**
- `backend/requirements.txt` — agrega `pytest`, `pytest-mock`.
- `backend/app/core/config.py` — agrega settings de Telegram/Gmail/umbral nuevo.
- `backend/app/etl/pipeline.py` — registra los scrapers huérfanos, arregla `run_incremental()`.
- `backend/app/etl/scrapers/dgii_scraper.py` — arregla el bug que nunca actualiza `cedula` en representantes ya existentes.
- `backend/app/services/alert_scanner.py` — arregla el bug de deduplicación de `EMPRESA_CONCENTRADA`, sube el umbral, agrega regla `NOMINA_DOBLE_COBRO`.

---

### Task 0: Guardar el trabajo pendiente y limpiar el huérfano

**Files:**
- Modify: (git add de los 19 archivos modificados + 6 sin rastrear, ver lista abajo)
- Delete: `backend/data/govtracker_test.db` (0 bytes, huérfano — el real está en `backend/govtracker_test.db`)

**Interfaces:** Ninguna — tarea de higiene de git, no toca código.

- [ ] **Step 1: Confirmar que no hay secretos en lo que se va a commitear**

Run: `cd /Users/branel/Desktop/GOB.DO && git ls-files | grep -c '^backend/\.env$'`
Expected: `0` (si no es 0, PARAR — no continuar sin resolver esto primero)

- [ ] **Step 2: Borrar el archivo huérfano**

```bash
rm backend/data/govtracker_test.db
```

- [ ] **Step 3: Commit del motor de detección (el más importante — nunca estuvo en git)**

```bash
git add backend/app/services/alert_scanner.py \
        backend/app/models/etl_run.py \
        backend/app/models/__init__.py \
        backend/app/etl/scrapers/hacienda_ejecucion_importer.py \
        backend/app/etl/scrapers/map_nominas_scraper.py \
        backend/app/api/routes/gasto_ejecutado.py \
        backend/app/api/routes/alerts.py \
        backend/app/api/routes/etl.py \
        backend/app/main.py

git commit -m "$(cat <<'EOF'
feat: versionar motor de alertas y modelo EtlRun (nunca estuvieron en git)

alert_scanner.py con las 8 reglas de detección y el modelo EtlRun para
auditar corridas existían solo en disco local. Sin esto, cualquier
automatización posterior no tiene nada real que ejecutar.
EOF
)"
```

- [ ] **Step 4: Commit del resto de rutas backend modificadas**

```bash
git add backend/app/api/routes/institutions.py \
        backend/app/api/routes/nominas.py \
        backend/app/api/routes/political_parties.py \
        backend/app/api/routes/seguros.py \
        backend/app/etl/scrapers/dgcp_bulk_importer.py \
        backend/app/etl/scrapers/hacienda_scraper.py

git commit -m "$(cat <<'EOF'
fix: ajustes en rutas de nóminas, instituciones, partidos y seguros

EOF
)"
```

- [ ] **Step 5: Commit del frontend**

```bash
git add frontend/src/App.tsx \
        frontend/src/components/Layout.tsx \
        frontend/src/pages/Nominas.tsx \
        frontend/src/pages/PoliticalParties.tsx \
        frontend/src/pages/Seguros.tsx \
        frontend/src/services/api.ts \
        frontend/src/pages/GastoEjecutado.tsx

git commit -m "feat: página de Gasto Ejecutado y ajustes de UI en Nóminas/Partidos/Seguros"
```

- [ ] **Step 6: Verificar que no quedó nada suelto**

Run: `git status --short`
Expected: vacío (o solo archivos nuevos que se crean en las tareas siguientes, que aún no existen)

---

### Task 1: Crear repo privado en GitHub y publicar

**Files:** Ninguno (acción de infraestructura).

- [ ] **Step 1: Crear el repo privado y añadir el remoto**

```bash
cd /Users/branel/Desktop/GOB.DO
gh repo create govtracker-rd --private --source=. --remote=origin --push
```

Expected: imprime la URL del repo creado (`https://github.com/<usuario>/govtracker-rd`) y hace push de `master`.

- [ ] **Step 2: Verificar**

Run: `gh repo view govtracker-rd --json isPrivate,url`
Expected: `"isPrivate": true`

---

### Task 2: Scaffolding de pytest

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_smoke.py`

**Interfaces:**
- Produces: fixture `db_session` (sqlite en memoria, todas las tablas creadas) — usada por todas las tareas siguientes.

- [ ] **Step 1: Agregar pytest a requirements**

Editar `backend/requirements.txt`, agregar al final:

```
pytest==8.2.2
pytest-mock==3.14.0
```

- [ ] **Step 2: Instalar y crear el fixture**

```bash
cd backend && pip install pytest==8.2.2 pytest-mock==3.14.0
mkdir -p tests
touch tests/__init__.py
```

`backend/tests/conftest.py`:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
import app.models  # noqa: F401 — registra todos los modelos en Base antes de create_all


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 3: Test trivial para verificar que el fixture funciona**

`backend/tests/test_smoke.py`:
```python
from app.models.institution import Institution


def test_db_session_crea_tablas_y_persiste(db_session):
    inst = Institution(nombre="Ministerio de Prueba", siglas="MDP")
    db_session.add(inst)
    db_session.commit()
    assert db_session.query(Institution).count() == 1
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_smoke.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/tests/
git commit -m "test: scaffolding de pytest con fixture de sqlite en memoria"
```

---

### Task 3: `orchestrator.py` — corridas diarias con `EtlRun` real

**Files:**
- Create: `backend/app/etl/orchestrator.py`
- Test: `backend/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `EtlRun` (de `app.models.etl_run`, campos: `fuente`, `iniciado_en`, `finalizado_en`, `estado`, `registros_nuevos`, `error`).
- Produces:
  - `@dataclass SourceResult(fuente: str, estado: str, registros_nuevos: int = 0, error: str | None = None)`
  - `@dataclass DailySource(nombre: str, is_async: bool, fn: Callable, kwargs: dict, extract_count: Callable[[Any], int])`
  - `DAILY_SOURCES: list[DailySource]` — usado por Task 8 (`scripts/investigar.py`).
  - `async def run_daily(db: Session, sources: list[DailySource] | None = None) -> list[SourceResult]`

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_orchestrator.py`:
```python
import pytest

from app.etl.orchestrator import run_daily, DailySource, SourceResult
from app.models.etl_run import EtlRun


def _ok_sync(**kwargs):
    return {"contratos": 7}


async def _ok_async(**kwargs):
    return 3


def _fail_sync(**kwargs):
    raise RuntimeError("portal caído")


@pytest.mark.asyncio
async def test_run_daily_registra_etl_run_por_fuente(db_session):
    sources = [
        DailySource("fuente_ok", False, _ok_sync, {}, lambda r: r["contratos"]),
        DailySource("fuente_async_ok", True, _ok_async, {}, lambda r: r),
    ]
    resultados = await run_daily(db_session, sources=sources)

    assert resultados == [
        SourceResult(fuente="fuente_ok", estado="ok", registros_nuevos=7),
        SourceResult(fuente="fuente_async_ok", estado="ok", registros_nuevos=3),
    ]
    runs = db_session.query(EtlRun).order_by(EtlRun.id).all()
    assert [r.fuente for r in runs] == ["fuente_ok", "fuente_async_ok"]
    assert all(r.estado == "ok" and r.finalizado_en is not None for r in runs)


@pytest.mark.asyncio
async def test_un_fallo_no_detiene_las_demas_fuentes(db_session):
    sources = [
        DailySource("rota", False, _fail_sync, {}, lambda r: r),
        DailySource("sana", False, _ok_sync, {}, lambda r: r["contratos"]),
    ]
    resultados = await run_daily(db_session, sources=sources)

    assert resultados[0].estado == "error"
    assert "portal caído" in resultados[0].error
    assert resultados[1].estado == "ok"
    assert resultados[1].registros_nuevos == 7

    runs = {r.fuente: r for r in db_session.query(EtlRun).all()}
    assert runs["rota"].estado == "error"
    assert runs["sana"].estado == "ok"
```

Agregar `pytest-asyncio` a requirements y a la config de pytest:
```bash
echo "pytest-asyncio==0.23.7" >> requirements.txt
pip install pytest-asyncio==0.23.7
```

`backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.etl.orchestrator'`

- [ ] **Step 3: Implementar**

`backend/app/etl/orchestrator.py`:
```python
"""
Orquestador de la corrida DIARIA (cron de GitHub Actions). A diferencia de
`ETLPipeline` (pipeline.py, disparado manualmente desde el panel), este
módulo registra un `EtlRun` por cada fuente y NUNCA deja que el fallo de
una fuente cancele las demás — antes, si un scraper lanzaba una excepción
sin capturar, toda la corrida moría y ninguna otra fuente se actualizaba.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from loguru import logger
from sqlalchemy.orm import Session

from ..models.etl_run import EtlRun
from .scrapers.dgcp_bulk_importer import run_dgcp_bulk_import
from .scrapers.hacienda_ejecucion_importer import run_import as run_hacienda_ejecucion
from .scrapers.camara_diputados_scraper import run_camara_diputados_scraper
from .scrapers.congreso_comisiones_scraper import run_congreso_comisiones_scraper
from .scrapers.pgr_scraper import run_pgr_scraper


@dataclass
class SourceResult:
    fuente: str
    estado: str  # "ok" | "error"
    registros_nuevos: int = 0
    error: Optional[str] = None


@dataclass
class DailySource:
    nombre: str
    is_async: bool
    fn: Callable[..., Any]
    kwargs: dict = field(default_factory=dict)
    extract_count: Callable[[Any], int] = lambda r: 0


# Las 5 fuentes de cadencia diaria. Nóminas (2.2GB, publicación mensual del
# MAP) tiene su propio ciclo — no entra aquí. Ver spec §3, decisión de
# tamaños/frecuencia.
DAILY_SOURCES: list[DailySource] = [
    DailySource("dgcp_bulk", False, run_dgcp_bulk_import, {"descargar": True},
                lambda r: r.get("contratos", 0)),
    DailySource("hacienda_ejecucion", False, run_hacienda_ejecucion, {"descargar": True},
                lambda r: r.get("detalle_nuevos", 0)),
    DailySource("camara_diputados", True, run_camara_diputados_scraper, {},
                lambda r: r),
    DailySource("congreso_comisiones", True, run_congreso_comisiones_scraper, {},
                lambda r: r),
    DailySource("pgr_comunicados", True, run_pgr_scraper, {"incremental": True},
                lambda r: r),
]


async def _run_one(db: Session, source: DailySource) -> SourceResult:
    run = EtlRun(fuente=source.nombre, estado="ok")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        if source.is_async:
            raw = await source.fn(**source.kwargs)
        else:
            raw = source.fn(**source.kwargs)
        count = source.extract_count(raw)
        run.registros_nuevos = count
        run.estado = "ok"
        resultado = SourceResult(fuente=source.nombre, estado="ok", registros_nuevos=count)
    except Exception as e:
        logger.error(f"ETL diario — {source.nombre} falló: {e}")
        run.estado = "error"
        run.error = str(e)[:2000]
        resultado = SourceResult(fuente=source.nombre, estado="error", error=str(e))
    run.finalizado_en = datetime.now(timezone.utc)
    db.commit()
    return resultado


async def run_daily(db: Session, sources: Optional[list[DailySource]] = None) -> list[SourceResult]:
    """Corre cada fuente diaria de forma INDEPENDIENTE, registrando un
    `EtlRun` por cada una. Llamar esto repetidamente es seguro: cada
    scraper subyacente ya deduplica por clave de negocio."""
    resultados = []
    for source in (sources if sources is not None else DAILY_SOURCES):
        resultados.append(await _run_one(db, source))
    return resultados
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/etl/orchestrator.py backend/tests/test_orchestrator.py backend/requirements.txt backend/pytest.ini
git commit -m "feat: orquestador diario con EtlRun real, fallos aislados por fuente"
```

---

### Task 4: Registrar scrapers huérfanos en `pipeline.py` y arreglar `run_incremental`

**Files:**
- Modify: `backend/app/etl/pipeline.py`
- Test: `backend/tests/test_pipeline_sources.py`

**Interfaces:**
- Consumes: `run_dgcp_bulk_import`, `run_hacienda_ejecucion` (alias de `run_import`) de Task 3.
- Produces: `ETLPipeline.DAILY_SOURCES: list[str]` (nombres, para que `run_incremental` filtre).

**Nota:** de los 8 scrapers huérfanos identificados en el spec, `punta_catalina_seed.py` NO se registra — es una semilla de un caso histórico único, sin función `run_*`, deliberadamente no recurrente (confirmado leyendo el archivo: no expone punto de entrada de pipeline).

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_pipeline_sources.py`:
```python
import pytest
from app.etl.pipeline import ETLPipeline


def test_dgcp_bulk_y_hacienda_ejecucion_estan_registrados():
    assert "dgcp_bulk" in ETLPipeline.ALL_SOURCES
    assert "hacienda_ejecucion" in ETLPipeline.ALL_SOURCES


def test_run_incremental_solo_corre_fuentes_diarias(monkeypatch):
    llamadas = []

    async def fake_run_full(self, sources=None):
        llamadas.append(sources)
        return {}

    monkeypatch.setattr(ETLPipeline, "run_full", fake_run_full)

    import asyncio
    asyncio.get_event_loop().run_until_complete(ETLPipeline().run_incremental())

    assert llamadas[0] == ETLPipeline.DAILY_SOURCES
    assert "seguridad" not in llamadas[0]  # fuente semilla estática, no diaria
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_pipeline_sources.py -v`
Expected: FAIL — `AttributeError: type object 'ETLPipeline' has no attribute 'ALL_SOURCES'`

- [ ] **Step 3: Implementar**

En `backend/app/etl/pipeline.py`, agregar imports después de la línea 17 (`from .scrapers.congreso_comisiones_scraper import run_congreso_comisiones_scraper`):

```python
from .scrapers.dgcp_bulk_importer import run_dgcp_bulk_import
from .scrapers.hacienda_ejecucion_importer import run_import as run_hacienda_ejecucion_import
from .scrapers.diputados_nominas_scraper import run_diputados_nominas_scraper
from .scrapers.map_nominas_scraper import run_map_nominas_scraper
from .scrapers.pgr_nominas_scraper import run_pgr_nominas_scraper
from .scrapers.pgr_scraper import run_pgr_scraper
from .scrapers.dgii_scraper import run_dgii_scraper
from datetime import datetime
```

Reemplazar la clase `ETLPipeline` completa (líneas 20-136) por:

```python
class ETLPipeline:

    # Fuentes de cadencia diaria — las que sí tiene sentido re-correr cada
    # día. Nóminas (2.2GB, mensual) y las semillas estáticas quedan fuera.
    DAILY_SOURCES: list = ["hacienda", "camara_diputados", "congreso_comisiones", "dgcp_bulk", "hacienda_ejecucion"]

    ALL_SOURCES: list = DAILY_SOURCES + [
        "credito_publico", "idecoop", "sib", "jce", "combustibles",
        "seguros_senasa", "seguridad", "dgcp",
        "diputados_nominas", "map_nominas", "pgr_nominas", "pgr_comunicados", "dgii",
    ]

    async def run_full(self, sources: list = None):
        """Ejecuta pipeline completo o subconjunto de fuentes."""
        sources = sources or self.ALL_SOURCES
        logger.info(f"Pipeline ETL iniciado: {sources}")
        results = {}

        if "hacienda" in sources:
            try:
                count = await run_hacienda_scraper()
                results["hacienda"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Hacienda pipeline error: {e}")
                results["hacienda"] = {"status": "error", "error": str(e)}

        if "credito_publico" in sources:
            try:
                count = await run_credito_publico_scraper()
                results["credito_publico"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Crédito Público pipeline error: {e}")
                results["credito_publico"] = {"status": "error", "error": str(e)}

        if "idecoop" in sources:
            try:
                count = await run_idecoop_scraper()
                results["idecoop"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"IDECOOP pipeline error: {e}")
                results["idecoop"] = {"status": "error", "error": str(e)}

        if "sib" in sources:
            try:
                count = await run_sib_scraper()
                results["sib"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"SIB pipeline error: {e}")
                results["sib"] = {"status": "error", "error": str(e)}

        if "jce" in sources:
            try:
                count = await run_jce_scraper()
                results["jce"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"JCE pipeline error: {e}")
                results["jce"] = {"status": "error", "error": str(e)}

        if "combustibles" in sources:
            try:
                count = await run_combustibles_scraper()
                results["combustibles"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Combustibles pipeline error: {e}")
                results["combustibles"] = {"status": "error", "error": str(e)}

        if "seguros_senasa" in sources:
            try:
                count = await run_seguros_senasa_scraper()
                results["seguros_senasa"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Seguros/SENASA pipeline error: {e}")
                results["seguros_senasa"] = {"status": "error", "error": str(e)}

        if "seguridad" in sources:
            try:
                count = await run_seguridad_scraper()
                results["seguridad"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Seguridad pipeline error: {e}")
                results["seguridad"] = {"status": "error", "error": str(e)}

        if "camara_diputados" in sources:
            try:
                count = await run_camara_diputados_scraper()
                results["camara_diputados"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Cámara de Diputados pipeline error: {e}")
                results["camara_diputados"] = {"status": "error", "error": str(e)}

        if "congreso_comisiones" in sources:
            try:
                count = await run_congreso_comisiones_scraper()
                results["congreso_comisiones"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Comisiones del Congreso pipeline error: {e}")
                results["congreso_comisiones"] = {"status": "error", "error": str(e)}

        if "dgcp" in sources:
            try:
                count = await run_dgcp_scraper(max_pages=50)
                results["dgcp"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"DGCP pipeline error: {e}")
                results["dgcp"] = {"status": "error", "error": str(e)}

        # ─── Antes huérfanos: no se disparaban desde ningún "correr todo" ───
        if "dgcp_bulk" in sources:
            try:
                r = run_dgcp_bulk_import(descargar=True)
                results["dgcp_bulk"] = {"status": "ok", "records": r.get("contratos", 0)}
            except Exception as e:
                logger.error(f"DGCP bulk import error: {e}")
                results["dgcp_bulk"] = {"status": "error", "error": str(e)}

        if "hacienda_ejecucion" in sources:
            try:
                r = run_hacienda_ejecucion_import(descargar=True)
                results["hacienda_ejecucion"] = {"status": "ok", "records": r.get("detalle_nuevos", 0)}
            except Exception as e:
                logger.error(f"Hacienda ejecución import error: {e}")
                results["hacienda_ejecucion"] = {"status": "error", "error": str(e)}

        if "diputados_nominas" in sources:
            try:
                r = await run_diputados_nominas_scraper()
                results["diputados_nominas"] = {"status": "ok", "records": r}
            except Exception as e:
                logger.error(f"Diputados nóminas error: {e}")
                results["diputados_nominas"] = {"status": "error", "error": str(e)}

        if "map_nominas" in sources:
            try:
                r = await run_map_nominas_scraper(anio=datetime.now().year)
                results["map_nominas"] = {"status": "ok", "records": r}
            except Exception as e:
                logger.error(f"MAP nóminas error: {e}")
                results["map_nominas"] = {"status": "error", "error": str(e)}

        if "pgr_nominas" in sources:
            try:
                r = await run_pgr_nominas_scraper()
                results["pgr_nominas"] = {"status": "ok", "records": r}
            except Exception as e:
                logger.error(f"PGR nóminas error: {e}")
                results["pgr_nominas"] = {"status": "error", "error": str(e)}

        if "pgr_comunicados" in sources:
            try:
                r = await run_pgr_scraper(incremental=True)
                results["pgr_comunicados"] = {"status": "ok", "records": r}
            except Exception as e:
                logger.error(f"PGR comunicados error: {e}")
                results["pgr_comunicados"] = {"status": "error", "error": str(e)}

        if "dgii" in sources:
            try:
                r = await run_dgii_scraper()
                results["dgii"] = {"status": "ok", "records": r}
            except Exception as e:
                logger.error(f"DGII enrichment error: {e}")
                results["dgii"] = {"status": "error", "error": str(e)}

        logger.info(f"Pipeline ETL completado: {results}")
        return results

    async def run_incremental(self):
        """Corre solo las fuentes de cadencia DIARIA. Antes era un alias
        vacío de run_full() — corría TODO (incluyendo nóminas de 2.2GB y
        semillas estáticas que no cambian) cada vez que se llamaba
        'incremental', lo cual no tenía sentido."""
        return await self.run_full(sources=self.DAILY_SOURCES)
```

(El resto del archivo — bloque de Celery tasks al final — no cambia.)

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_pipeline_sources.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/etl/pipeline.py backend/tests/test_pipeline_sources.py
git commit -m "feat: registrar 6 scrapers huérfanos en pipeline.py, run_incremental ya no es alias de run_full"
```

---

### Task 5: `alert_diff.py`

**Files:**
- Create: `backend/app/services/alert_diff.py`
- Test: `backend/tests/test_alert_diff.py`

**Interfaces:**
- Consumes: `Alert`, `AlertSeverity` (de `app.models.alert`).
- Produces: `def get_new_alerts(db: Session, since: datetime) -> list[Alert]` — usado por Task 8.

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_alert_diff.py`:
```python
from datetime import datetime, timedelta, timezone

from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.alert_diff import get_new_alerts


def _alert(db, *, created_at, severidad=AlertSeverity.MEDIA, titulo="x"):
    a = Alert(
        tipo=AlertType.CONTRATO_GRANDE, severidad=severidad, titulo=titulo,
        entidad_tipo="contrato", entidad_id=1, created_at=created_at,
    )
    db.add(a)
    db.commit()
    return a


def test_solo_devuelve_alertas_posteriores_a_since(db_session):
    corte = datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc)
    _alert(db_session, created_at=corte - timedelta(days=1), titulo="vieja")
    nueva = _alert(db_session, created_at=corte + timedelta(minutes=1), titulo="nueva")

    resultado = get_new_alerts(db_session, since=corte)

    assert [a.titulo for a in resultado] == ["nueva"]


def test_ordena_por_severidad_critica_primero(db_session):
    corte = datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc)
    _alert(db_session, created_at=corte + timedelta(minutes=1), severidad=AlertSeverity.MEDIA, titulo="media")
    _alert(db_session, created_at=corte + timedelta(minutes=2), severidad=AlertSeverity.CRITICA, titulo="critica")
    _alert(db_session, created_at=corte + timedelta(minutes=3), severidad=AlertSeverity.ALTA, titulo="alta")

    resultado = get_new_alerts(db_session, since=corte)

    assert [a.titulo for a in resultado] == ["critica", "alta", "media"]
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_alert_diff.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.alert_diff'`

- [ ] **Step 3: Implementar**

`backend/app/services/alert_diff.py`:
```python
"""
Aísla qué alertas son NUEVAS desde la última corrida. Sin esto, notificar
cada día repetiría las 33,897 alertas históricas en vez de solo lo que
cambió hoy — el error #1 que mataría la utilidad del sistema (ver spec,
riesgo R1: fatiga de alertas).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.alert import Alert, AlertSeverity

_ORDEN_SEVERIDAD = {
    AlertSeverity.CRITICA: 0,
    AlertSeverity.ALTA: 1,
    AlertSeverity.MEDIA: 2,
    AlertSeverity.BAJA: 3,
}


def get_new_alerts(db: Session, since: datetime) -> list[Alert]:
    """Alertas creadas estrictamente después de `since`, ordenadas por
    severidad (CRÍTICA primero) y luego por fecha de creación."""
    alertas = db.query(Alert).filter(Alert.created_at > since).all()
    return sorted(alertas, key=lambda a: (_ORDEN_SEVERIDAD.get(a.severidad, 9), a.created_at))
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_alert_diff.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/alert_diff.py backend/tests/test_alert_diff.py
git commit -m "feat: alert_diff — aísla alertas nuevas desde la última corrida"
```

---

### Task 6: `digest.py`

**Files:**
- Create: `backend/app/services/digest.py`
- Test: `backend/tests/test_digest.py`

**Interfaces:**
- Consumes: `Alert`, `AlertSeverity` (de `app.models.alert`).
- Produces: `def build_digest(alerts: list[Alert]) -> str` — usado por Task 8. Devuelve `""` si `alerts` está vacío.

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_digest.py`:
```python
from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.digest import build_digest


def _alert(severidad, titulo, monto=None):
    return Alert(tipo=AlertType.CONTRATO_GRANDE, severidad=severidad, titulo=titulo,
                 entidad_tipo="contrato", entidad_id=1, monto_involucrado=monto)


def test_lista_vacia_devuelve_string_vacio():
    assert build_digest([]) == ""


def test_agrupa_por_severidad_critica_primero():
    alertas = [
        _alert(AlertSeverity.MEDIA, "hallazgo medio"),
        _alert(AlertSeverity.CRITICA, "hallazgo critico"),
    ]
    texto = build_digest(alertas)

    assert texto.index("CRÍTICA") < texto.index("MEDIA")
    assert "hallazgo critico" in texto
    assert "hallazgo medio" in texto


def test_incluye_monto_formateado_cuando_existe():
    texto = build_digest([_alert(AlertSeverity.ALTA, "contrato grande", monto=150_000_000)])
    assert "RD$150,000,000" in texto


def test_trunca_a_20_por_severidad_y_avisa_cuantos_mas():
    alertas = [_alert(AlertSeverity.MEDIA, f"hallazgo {i}") for i in range(25)]
    texto = build_digest(alertas)

    assert "hallazgo 0" in texto
    assert "hallazgo 19" in texto
    assert "hallazgo 20" not in texto
    assert "y 5 más" in texto
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_digest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.digest'`

- [ ] **Step 3: Implementar**

`backend/app/services/digest.py`:
```python
"""Formatea una lista de alertas en texto plano agrupado por severidad,
listo para enviar por Telegram o correo."""
from ..models.alert import Alert, AlertSeverity

_ORDEN = [AlertSeverity.CRITICA, AlertSeverity.ALTA, AlertSeverity.MEDIA, AlertSeverity.BAJA]
_ETIQUETA = {
    AlertSeverity.CRITICA: "🔴 CRÍTICA",
    AlertSeverity.ALTA: "🟠 ALTA",
    AlertSeverity.MEDIA: "🟡 MEDIA",
    AlertSeverity.BAJA: "⚪ BAJA",
}
_MAX_POR_SEVERIDAD = 20


def build_digest(alerts: list[Alert]) -> str:
    """Cadena vacía si no hay alertas — el llamador decide no enviar nada
    en ese caso (un digest de '0 hallazgos' a diario entrena a ignorarlo)."""
    if not alerts:
        return ""

    por_severidad: dict[AlertSeverity, list[Alert]] = {s: [] for s in _ORDEN}
    for a in alerts:
        por_severidad.setdefault(a.severidad, []).append(a)

    lineas = [f"Investigador GovTracker — {len(alerts)} hallazgo(s) nuevo(s)", ""]
    for severidad in _ORDEN:
        grupo = por_severidad.get(severidad, [])
        if not grupo:
            continue
        lineas.append(f"{_ETIQUETA[severidad]} ({len(grupo)})")
        for a in grupo[:_MAX_POR_SEVERIDAD]:
            monto = f" — RD${a.monto_involucrado:,.0f}" if a.monto_involucrado else ""
            lineas.append(f"  • {a.titulo}{monto}")
        if len(grupo) > _MAX_POR_SEVERIDAD:
            lineas.append(f"  … y {len(grupo) - _MAX_POR_SEVERIDAD} más")
        lineas.append("")
    return "\n".join(lineas).strip()
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_digest.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/digest.py backend/tests/test_digest.py
git commit -m "feat: digest.py — formatea alertas agrupadas por severidad"
```

---

### Task 7: `notifier.py` + settings de Telegram/Gmail

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/notifier.py`
- Test: `backend/tests/test_notifier.py`

**Interfaces:**
- Produces: `class TelegramNotifier`, `class GmailNotifier` (ambas con `.send(text: str) -> None`), `def get_notifiers() -> list` — usado por Task 8.

- [ ] **Step 1: Agregar settings**

En `backend/app/core/config.py`, agregar después de `ALERT_CAPTIVE_MIN_MONTO: float = 50_000_000`:

```python
    ALERT_CONCENTRACION_MIN_MONTO: float = 20_000_000  # ver Task 12 — umbral calibrado con datos reales

    # Notificaciones
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    GMAIL_USER: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None
    ALERT_EMAIL_TO: Optional[str] = None
```

- [ ] **Step 2: Escribir el test que falla**

`backend/tests/test_notifier.py`:
```python
import smtplib

from app.services import notifier as notifier_module
from app.services.notifier import TelegramNotifier, GmailNotifier, get_notifiers


def test_telegram_notifier_envia_al_endpoint_correcto(monkeypatch):
    llamadas = []

    def fake_post(url, json, timeout):
        llamadas.append((url, json))
        class FakeResp:
            def raise_for_status(self): pass
        return FakeResp()

    monkeypatch.setattr(notifier_module.httpx, "post", fake_post)

    TelegramNotifier("TOKEN123", "999").send("hola mundo")

    url, payload = llamadas[0]
    assert url == "https://api.telegram.org/botTOKEN123/sendMessage"
    assert payload == {"chat_id": "999", "text": "hola mundo"}


def test_gmail_notifier_usa_smtp_ssl_465(monkeypatch):
    envios = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            envios["host"] = host
            envios["port"] = port
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, user, password):
            envios["login"] = (user, password)
        def sendmail(self, from_addr, to_addrs, msg):
            envios["sendmail"] = (from_addr, to_addrs)

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)

    GmailNotifier("bot@gmail.com", "app-pass", "destino@gmail.com").send("cuerpo")

    assert envios["host"] == "smtp.gmail.com"
    assert envios["port"] == 465
    assert envios["login"] == ("bot@gmail.com", "app-pass")
    assert envios["sendmail"] == ("bot@gmail.com", ["destino@gmail.com"])


def test_get_notifiers_solo_instancia_lo_configurado(monkeypatch):
    monkeypatch.setattr(notifier_module.settings, "TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setattr(notifier_module.settings, "TELEGRAM_CHAT_ID", "c")
    monkeypatch.setattr(notifier_module.settings, "GMAIL_USER", None)
    monkeypatch.setattr(notifier_module.settings, "GMAIL_APP_PASSWORD", None)
    monkeypatch.setattr(notifier_module.settings, "ALERT_EMAIL_TO", None)

    notifiers = get_notifiers()

    assert len(notifiers) == 1
    assert isinstance(notifiers[0], TelegramNotifier)


def test_get_notifiers_vacio_sin_ninguna_credencial(monkeypatch):
    for campo in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GMAIL_USER", "GMAIL_APP_PASSWORD", "ALERT_EMAIL_TO"]:
        monkeypatch.setattr(notifier_module.settings, campo, None)

    assert get_notifiers() == []
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_notifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.notifier'`

- [ ] **Step 4: Implementar**

`backend/app/services/notifier.py`:
```python
"""
Canales de aviso. `get_notifiers()` solo instancia los que tienen
credenciales configuradas — así el sistema funciona con Telegram solo,
Gmail solo, ambos, o ninguno (el digest se genera igual, simplemente no
se envía por ningún canal si no hay credenciales).

Gmail queda con código completo pero SIN activar hasta que se agreguen
GMAIL_USER/GMAIL_APP_PASSWORD/ALERT_EMAIL_TO (decisión del usuario,
15/07/26: enfocar primero en Telegram).
"""
import smtplib
from email.mime.text import MIMEText
from typing import Protocol

import httpx
from loguru import logger

from ..core.config import settings


class Notifier(Protocol):
    def send(self, text: str) -> None: ...


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        resp = httpx.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=15)
        resp.raise_for_status()


class GmailNotifier:
    def __init__(self, user: str, app_password: str, to_email: str,
                 subject: str = "GovTracker — hallazgos nuevos"):
        self.user = user
        self.app_password = app_password
        self.to_email = to_email
        self.subject = subject

    def send(self, text: str) -> None:
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = self.subject
        msg["From"] = self.user
        msg["To"] = self.to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(self.user, self.app_password)
            server.sendmail(self.user, [self.to_email], msg.as_string())


def get_notifiers() -> list:
    notifiers = []
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        notifiers.append(TelegramNotifier(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID))
    else:
        logger.info("Telegram no configurado (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes)")
    if settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD and settings.ALERT_EMAIL_TO:
        notifiers.append(GmailNotifier(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD, settings.ALERT_EMAIL_TO))
    return notifiers
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_notifier.py -v`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/services/notifier.py backend/tests/test_notifier.py
git commit -m "feat: notifier.py — Telegram activo, Gmail listo pero sin credenciales"
```

---

### Task 8: `scripts/investigar.py` — entrypoint del cron

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/investigar.py`
- Test: `backend/tests/test_investigar.py`

**Interfaces:**
- Consumes: `run_daily`/`DailySource` (Task 3), `run_alert_scan` (existente), `get_new_alerts` (Task 5), `build_digest` (Task 6), `get_notifiers`/`Notifier` (Task 7).
- Produces: `async def main(sources=None, notifiers_override=None) -> int` — parámetros opcionales solo para testeo; en producción (`__main__`) se llama sin argumentos y usa los reales.

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_investigar.py`:
```python
from datetime import datetime, timezone

from app.etl.orchestrator import DailySource
from app.models.contract import Contract, ContractStatus
from scripts.investigar import main


def _seed_contrato_que_dispara_alerta(db):
    """CONTRATO_GRANDE: monto >= 100M vía contratación directa — regla #1
    de alert_scanner.py, la más simple de disparar sin datos externos."""
    c = Contract(
        numero_contrato="TEST-001", modalidad="contratacion_directa",
        monto_original=150_000_000, moneda="DOP", estado=ContractStatus.VIGENTE,
    )
    db.add(c)
    db.commit()


class FakeNotifier:
    def __init__(self):
        self.enviados = []
    def send(self, text):
        self.enviados.append(text)


async def test_main_envia_digest_cuando_hay_alertas_nuevas(db_session, monkeypatch):
    monkeypatch.setattr("scripts.investigar.SessionLocal", lambda: db_session)
    monkeypatch.setattr("scripts.investigar.Base", type("B", (), {"metadata": type("M", (), {"create_all": lambda **k: None})()}))

    _seed_contrato_que_dispara_alerta(db_session)
    fake = FakeNotifier()

    codigo = await main(sources=[], notifiers_override=[fake])

    assert codigo == 0
    assert len(fake.enviados) == 1
    assert "CONTRATO_GRANDE" in fake.enviados[0] or "Contrato directo" in fake.enviados[0]


async def test_main_no_envia_nada_sin_hallazgos_nuevos(db_session, monkeypatch):
    monkeypatch.setattr("scripts.investigar.SessionLocal", lambda: db_session)
    monkeypatch.setattr("scripts.investigar.Base", type("B", (), {"metadata": type("M", (), {"create_all": lambda **k: None})()}))

    fake = FakeNotifier()
    codigo = await main(sources=[], notifiers_override=[fake])

    assert codigo == 0
    assert fake.enviados == []
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_investigar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.investigar'`

- [ ] **Step 3: Implementar**

`backend/scripts/__init__.py`: (vacío)

`backend/scripts/investigar.py`:
```python
"""
Entrypoint del cron diario (ver .github/workflows/investigar.yml). Se
ejecuta con:
    python -m scripts.investigar
Un fallo de UNA fuente no hace fallar el script completo — eso ya lo
tolera el orquestador y queda registrado en `etl_runs`. El script solo
devuelve código distinto de 0 si algo revienta fuera de ese manejo (bug
real, no un portal caído).
"""
import asyncio
import sys
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.core.database import SessionLocal, Base, engine
import app.models  # noqa: F401 — registra todos los modelos antes de create_all
from app.etl.orchestrator import run_daily, DailySource
from app.services.alert_scanner import run_alert_scan
from app.services.alert_diff import get_new_alerts
from app.services.digest import build_digest
from app.services.notifier import get_notifiers


async def main(
    sources: Optional[list[DailySource]] = None,
    notifiers_override: Optional[list] = None,
) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    inicio = datetime.now(timezone.utc)
    try:
        resultados = await run_daily(db, sources=sources)
        for r in resultados:
            detalle = f" — {r.error}" if r.error else ""
            logger.info(f"{r.fuente}: {r.estado} ({r.registros_nuevos} nuevos){detalle}")

        run_alert_scan(db)

        nuevas = get_new_alerts(db, since=inicio)
        texto = build_digest(nuevas)
        notifiers = notifiers_override if notifiers_override is not None else get_notifiers()
        if texto:
            for notifier in notifiers:
                try:
                    notifier.send(texto)
                except Exception as e:
                    logger.error(f"Notificador {type(notifier).__name__} falló: {e}")
        else:
            logger.info("Sin hallazgos nuevos — no se envía nada.")

        fallos = [r for r in resultados if r.estado == "error"]
        if fallos:
            logger.warning(f"{len(fallos)} fuente(s) fallaron esta corrida: {[r.fuente for r in fallos]}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_investigar.py -v`
Expected: `2 passed`

- [ ] **Step 5: Correrlo de verdad en local, contra la BD real, SIN fuentes de red (smoke test end-to-end)**

Run: `cd backend && python -c "
import asyncio
from scripts.investigar import main
codigo = asyncio.run(main(sources=[]))
print('código de salida:', codigo)
"`
Expected: corre sin excepción, imprime `código de salida: 0`, y loguea cuántas alertas nuevas encontró (probablemente 0, porque `alert_scanner` ya vio todo lo que hay hoy) o las envía si `get_notifiers()` ya tiene Telegram configurado en el `.env` local.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/ backend/tests/test_investigar.py
git commit -m "feat: scripts/investigar.py — entrypoint del cron diario"
```

---

### Task 9: GitHub Actions — `.github/workflows/investigar.yml`

**Files:**
- Create: `.github/workflows/investigar.yml`

**Interfaces:** Ninguna — configuración de CI.

- [ ] **Step 1: Escribir el workflow**

`.github/workflows/investigar.yml`:
```yaml
name: Investigador diario

on:
  schedule:
    - cron: "0 10 * * *"  # 10:00 UTC = 06:00 AST
  workflow_dispatch: {}

jobs:
  investigar:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Restaurar BD desde caché
        id: cache-db
        uses: actions/cache@v4
        with:
          path: backend/govtracker_test.db
          key: govtracker-db-${{ github.run_id }}
          restore-keys: |
            govtracker-db-

      - name: Instalar dependencias
        run: pip install -r requirements.txt

      - name: Preparar .env mínimo para sqlite
        run: |
          echo "DATABASE_URL=sqlite:///./govtracker_test.db" >> .env
          echo "DATABASE_URL_ASYNC=sqlite+aiosqlite:///./govtracker_test.db" >> .env

      - name: Correr investigador
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          ALERT_EMAIL_TO: ${{ secrets.ALERT_EMAIL_TO }}
        run: python -m scripts.investigar

      - name: Guardar BD en caché
        if: always()
        uses: actions/cache/save@v4
        with:
          path: backend/govtracker_test.db
          key: govtracker-db-${{ github.run_id }}
```

**Nota:** si la caché nunca existió (primera corrida), no hay `restore` — el script arranca sin `govtracker_test.db`, `Base.metadata.create_all` lo crea vacío, y `dgcp_bulk_importer`/`hacienda_ejecucion_importer` con `descargar=True` reconstruyen todo desde los CSV oficiales. Más lenta esa corrida, pero nunca rota.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/investigar.yml
git commit -m "feat: cron diario en GitHub Actions con caché de BD sqlite"
```

- [ ] **Step 3: Disparo manual de verificación (requiere el repo ya empujado — Task 1)**

Run: `gh workflow run investigar.yml && sleep 20 && gh run list --workflow=investigar.yml --limit 1`
Expected: aparece una corrida en estado `in_progress` o `completed`. Revisar con `gh run watch` hasta verde. Si falla por secretos de Telegram ausentes, es esperado hasta completar Task 13 — el resto del workflow (ETL + EtlRun) debe pasar igual.

---

### Task 10: Arreglar el bug de `dgii_scraper` que nunca actualiza `cedula` en representantes existentes

**Files:**
- Modify: `backend/app/etl/scrapers/dgii_scraper.py`
- Test: `backend/tests/test_dgii_cedula_backfill.py`

**Interfaces:** Ninguna nueva — corrige comportamiento interno de `DGIIScraper._update_company`.

**Contexto del bug (verificado leyendo el código, spec §3.1):** `_update_company` solo crea un `LegalRepresentative` nuevo `if not existing` — si ya existe una fila con ese `(company_id, nombre)` (que es el caso de las 123,128 filas actuales, todas con `cedula` vacía porque las creó el importador de DGCP, no DGII), el código simplemente la ignora. Nunca hay backfill.

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_dgii_cedula_backfill.py`:
```python
import pytest

from app.models.company import Company, LegalRepresentative
from app.etl.scrapers.dgii_scraper import DGIIScraper


def test_backfillea_cedula_en_representante_existente_sin_cedula(db_session, monkeypatch):
    comp = Company(nombre="Empresa Test", rnc="123456789")
    db_session.add(comp)
    db_session.commit()

    rep = LegalRepresentative(company_id=comp.id, nombre="Juan Pérez", cedula="")
    db_session.add(rep)
    db_session.commit()

    scraper = DGIIScraper()
    monkeypatch.setattr(scraper, "db", db_session)

    scraper._update_company(comp, {"representante": "Juan Pérez", "cedula_repr": "001-1234567-8"})
    db_session.commit()

    db_session.refresh(rep)
    assert rep.cedula == "001-1234567-8"


def test_no_pisa_cedula_ya_correcta_con_vacio(db_session, monkeypatch):
    comp = Company(nombre="Empresa Test 2", rnc="987654321")
    db_session.add(comp)
    db_session.commit()

    rep = LegalRepresentative(company_id=comp.id, nombre="Ana Gómez", cedula="001-9999999-9")
    db_session.add(rep)
    db_session.commit()

    scraper = DGIIScraper()
    monkeypatch.setattr(scraper, "db", db_session)

    scraper._update_company(comp, {"representante": "Ana Gómez", "cedula_repr": ""})
    db_session.commit()

    db_session.refresh(rep)
    assert rep.cedula == "001-9999999-9"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_dgii_cedula_backfill.py -v`
Expected: FAIL en el primer test (`assert rep.cedula == "001-1234567-8"` — sigue siendo `""`)

- [ ] **Step 3: Implementar el fix**

En `backend/app/etl/scrapers/dgii_scraper.py`, reemplazar el bloque (líneas 169-183):

```python
        # Representante legal — el dato más valioso
        repr_nombre = data.get("representante", "").strip()
        if repr_nombre:
            # Verificar si ya existe
            existing = self.db.query(LegalRepresentative).filter(
                LegalRepresentative.company_id == comp.id,
                LegalRepresentative.nombre == repr_nombre,
            ).first()
            if not existing:
                rep = LegalRepresentative(
                    company_id=comp.id,
                    nombre=repr_nombre,
                    cedula=data.get("cedula_repr", ""),
                    cargo="Representante Legal (DGII)",
                )
                self.db.add(rep)
                logger.info(f"  ✓ Representante DGII: {repr_nombre} → {comp.nombre[:40]}")
```

por:

```python
        # Representante legal — el dato más valioso
        repr_nombre = data.get("representante", "").strip()
        cedula_nueva = (data.get("cedula_repr") or "").strip()
        if repr_nombre:
            existing = self.db.query(LegalRepresentative).filter(
                LegalRepresentative.company_id == comp.id,
                LegalRepresentative.nombre == repr_nombre,
            ).first()
            if not existing:
                rep = LegalRepresentative(
                    company_id=comp.id,
                    nombre=repr_nombre,
                    cedula=cedula_nueva,
                    cargo="Representante Legal (DGII)",
                )
                self.db.add(rep)
                logger.info(f"  ✓ Representante DGII: {repr_nombre} → {comp.nombre[:40]}")
            elif cedula_nueva and not (existing.cedula or "").strip():
                # Backfill: la fila ya existía (normalmente creada por el
                # importador de DGCP, que no trae cédula) pero le faltaba
                # cédula y DGII sí la tiene — sin esto, ~123K representantes
                # se quedan sin identidad verificable para siempre.
                existing.cedula = cedula_nueva
                logger.info(f"  ✓ Cédula rellenada para {repr_nombre}: {cedula_nueva}")
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_dgii_cedula_backfill.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/etl/scrapers/dgii_scraper.py backend/tests/test_dgii_cedula_backfill.py
git commit -m "fix: dgii_scraper ahora rellena cedula en representantes ya existentes

Antes _update_company solo creaba representantes nuevos; si el
representante ya existía (el caso normal, creado por DGCP sin cédula),
la cédula de DGII se descartaba en silencio. 123,128 representantes
tienen cedula vacía hoy por este bug."
```

---

### Task 11: Consolidar `NOMINA_DOBLE_COBRO` dentro de `alert_scanner.py`

**Files:**
- Modify: `backend/app/services/alert_scanner.py`
- Modify: `backend/app/models/alert.py` (agregar tipo nuevo)
- Test: `backend/tests/test_nomina_doble_cobro.py`

**Interfaces:**
- Produces: nueva regla dentro de `run_alert_scan` que usa `_scan_nomina_doble_cobro(db, nominas_db_path)`.

**Contexto:** La lógica de "doble cobro" (misma persona, mismo mes, más de una institución) ya existe y funciona en `api/routes/nominas.py::doble_cobro` — pero vive suelta ahí, no alimenta la tabla `Alert` ni pasa por el pipeline de detección. `nominas.db` es una BD sqlite **separada** (2.2GB, no en git, no en CI) — la función debe tolerar que el archivo no exista y no fallar la corrida completa si falta.

**Precisión (spec §3, riesgo R2 — no negociable):** solo se generan alertas para el nivel de confianza `ALTA` (nombres largos y específicos, mismo heurístico que ya usa `doble_cobro` en producción) y el texto SIEMPRE dice "coincidencia por nombre, sin cédula que confirme identidad" — igual que ya hace `POSIBLE_CONFLICTO`.

- [ ] **Step 1: Agregar el tipo de alerta**

En `backend/app/models/alert.py`, agregar dentro de `class AlertType`:
```python
    NOMINA_DOBLE_COBRO = "nomina_doble_cobro"
```

- [ ] **Step 2: Escribir el test que falla**

`backend/tests/test_nomina_doble_cobro.py`:
```python
import sqlite3

from app.models.alert import Alert, AlertType
from app.services.alert_scanner import _scan_nomina_doble_cobro


def _crear_nominas_db(tmp_path):
    db_path = tmp_path / "nominas_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE empleados (
            id INTEGER PRIMARY KEY, institucion TEXT, nombre_raw TEXT,
            nombre TEXT, funcion TEXT, salario REAL, mes INTEGER, anio INTEGER, fuente TEXT
        )
    """)
    # Nombre largo (>22 chars normalizado) = confianza ALTA, cobrando en 2 instituciones el mismo mes
    conn.executemany(
        "INSERT INTO empleados (institucion, nombre_raw, nombre, funcion, salario, mes, anio, fuente) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("MINISTERIO DE SALUD", "Juan Carlos Perez Gonzalez", "JUAN CARLOS PEREZ GONZALEZ", "MEDICO", 80000, 6, 2026, "test"),
            ("MINISTERIO DE EDUCACION", "Juan Carlos Perez Gonzalez", "JUAN CARLOS PEREZ GONZALEZ", "PROFESOR", 60000, 6, 2026, "test"),
            # Nombre corto = confianza BAJA, no debe generar alerta
            ("MINISTERIO DE SALUD", "Ana Ruiz", "ANA RUIZ", "ENFERMERA", 40000, 6, 2026, "test"),
            ("MINISTERIO DE EDUCACION", "Ana Ruiz", "ANA RUIZ", "PROFESORA", 35000, 6, 2026, "test"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_genera_alerta_solo_para_confianza_alta(db_session, tmp_path):
    nominas_path = _crear_nominas_db(tmp_path)

    nuevas = _scan_nomina_doble_cobro(db_session, nominas_db_path=nominas_path)

    assert len(nuevas) == 1
    assert nuevas[0].tipo == AlertType.NOMINA_DOBLE_COBRO
    assert "JUAN CARLOS PEREZ GONZALEZ" in nuevas[0].titulo.upper() or "JUAN CARLOS PEREZ GONZALEZ" in nuevas[0].descripcion.upper()
    assert "sin cédula" in nuevas[0].descripcion.lower()


def test_no_falla_si_nominas_db_no_existe(db_session, tmp_path):
    ruta_inexistente = tmp_path / "no_existe.db"
    assert _scan_nomina_doble_cobro(db_session, nominas_db_path=ruta_inexistente) == []


def test_es_seguro_llamarlo_dos_veces_no_duplica(db_session, tmp_path):
    nominas_path = _crear_nominas_db(tmp_path)

    primera = _scan_nomina_doble_cobro(db_session, nominas_db_path=nominas_path)
    db_session.commit()
    segunda = _scan_nomina_doble_cobro(db_session, nominas_db_path=nominas_path)

    assert len(primera) == 1
    assert len(segunda) == 0
    assert db_session.query(Alert).filter(Alert.tipo == AlertType.NOMINA_DOBLE_COBRO).count() == 1
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_nomina_doble_cobro.py -v`
Expected: FAIL — `ImportError: cannot import name '_scan_nomina_doble_cobro'`

- [ ] **Step 4: Implementar**

En `backend/app/services/alert_scanner.py`, agregar al inicio (tras los imports existentes):
```python
import sqlite3
import unicodedata
import re
from pathlib import Path

NOMINAS_DB_DEFAULT = Path(__file__).parent.parent.parent.parent / "data" / "nominas.db"


def _norm_nombre(s: str) -> str:
    n = (s or "").upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^A-Z\s]", "", n)
    return n.strip()


def _scan_nomina_doble_cobro(db: Session, nominas_db_path: Path = NOMINAS_DB_DEFAULT) -> list[Alert]:
    """Misma persona cobrando en >1 institución el mismo mes. Reutiliza el
    heurístico de confianza ya validado en producción por
    `api/routes/nominas.py::doble_cobro` (nombre normalizado más largo =
    más específico = menos probable que sea coincidencia de homónimos) —
    pero antes esta lógica nunca alimentaba la tabla Alert. Solo genera
    alerta para confianza ALTA: es una regla nueva, hay que estrenarla con
    el listón más exigente, no con el más ruidoso.

    Tolera que `nominas.db` no exista (2.2GB, no vive en CI) — devuelve
    lista vacía en vez de romper toda la corrida."""
    if not Path(nominas_db_path).exists():
        return []

    conn = sqlite3.connect(str(nominas_db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT nombre, MIN(nombre_raw) AS nombre_raw,
                   COUNT(*) AS meses_afectados,
                   GROUP_CONCAT(DISTINCT instituciones_mes) AS instituciones,
                   ROUND(SUM(total_mes), 0) AS total_cobrado
            FROM (
                SELECT nombre, MIN(nombre_raw) AS nombre_raw, anio, mes,
                       COUNT(DISTINCT institucion) AS num_inst,
                       GROUP_CONCAT(DISTINCT institucion) AS instituciones_mes,
                       SUM(salario) AS total_mes
                FROM empleados
                WHERE anio BETWEEN 2010 AND 2026
                GROUP BY nombre, anio, mes
                HAVING num_inst > 1 AND nombre != '' AND LENGTH(nombre) > 22
            ) sub
            GROUP BY nombre
        """).fetchall()
    finally:
        conn.close()

    nuevas: list[Alert] = []
    for r in rows:
        key = abs(hash(r["nombre"])) % 2_000_000_000
        if _alert_exists(db, AlertType.NOMINA_DOBLE_COBRO, key):
            continue
        nuevas.append(_add(db, Alert(
            tipo=AlertType.NOMINA_DOBLE_COBRO,
            severidad=AlertSeverity.ALTA,
            titulo=f"Posible doble cobro en nómina: {r['nombre_raw']}",
            descripcion=(
                f"«{r['nombre_raw']}» aparece cobrando en {r['instituciones']} durante "
                f"{r['meses_afectados']} mes(es), por un total de {_fmt(r['total_cobrado'] or 0)} — "
                f"coincidencia por nombre, sin cédula que confirme identidad; requiere verificación "
                f"manual antes de concluir doble cobro indebido"
            ),
            entidad_tipo="persona_nomina", entidad_id=key,
            entidad_nombre=r["nombre_raw"],
            monto_involucrado=r["total_cobrado"],
            datos_extra={"instituciones": r["instituciones"], "verificado": False},
        )))
    db.commit()
    return nuevas
```

Y dentro de `run_alert_scan`, justo antes de `db.commit()` / `return nuevas` (final de la función, línea 211), agregar:
```python
    nuevas.extend(_scan_nomina_doble_cobro(db))
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_nomina_doble_cobro.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/alert_scanner.py backend/app/models/alert.py backend/tests/test_nomina_doble_cobro.py
git commit -m "feat: regla NOMINA_DOBLE_COBRO — consolida doble-cobro de nominas.py en el motor de alertas

Solo confianza ALTA, siempre marcada 'sin cédula que confirme identidad'
(regla no negociable del spec, riesgo R2: evitar acusar homónimos)."
```

---

### Task 12: Arreglar el bug de deduplicación de `EMPRESA_CONCENTRADA` + subir el umbral con datos reales

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/alert_scanner.py`
- Test: `backend/tests/test_alert_scanner_empresa_concentrada.py`

**Contexto del bug (verificado con SQL directo contra `govtracker_test.db`, no hipotético):**
- Hoy hay **26,490** alertas `EMPRESA_CONCENTRADA` guardadas, pero solo **2,230** valores distintos de `entidad_id` — una sola empresa (id `128050`) tiene **410 filas duplicadas**.
- Causa: el código chequea existencia con una clave compuesta (`key = company_id * 100000 + institution_id`) pero **guarda** `entidad_id=company_id` (sin componer). `_alert_exists` nunca encuentra coincidencia real, así que cada corrida vuelve a crear la alerta para los mismos pares empresa-institución.
- Distribución real verificada por SQL: con el umbral actual (`cnt >= 20`) hay **5,298** grupos empresa-institución; exigiendo además `monto >= RD$20M` (agregar `ALERT_CONCENTRACION_MIN_MONTO`) baja a **466** — ese es el número, no un valor inventado.
- `PROVEEDOR_INHABILITADO` fue auditado (spec sugería posible bug de fecha): se verificó con SQL que **0** contratos quedaron mal marcados con `fecha_firma < fecha_inhabilitacion`. **No tiene bug — no se toca.**

- [ ] **Step 1: Agregar el umbral de monto (ya agregado en Task 7 — verificar)**

Confirmar que `backend/app/core/config.py` tiene `ALERT_CONCENTRACION_MIN_MONTO: float = 20_000_000` (se agregó en Task 7, Step 1). Si no, agregarlo ahora.

- [ ] **Step 2: Escribir el test que falla**

`backend/tests/test_alert_scanner_empresa_concentrada.py`:
```python
from app.models.company import Company
from app.models.contract import Contract, ContractStatus
from app.models.alert import Alert, AlertType
from app.services.alert_scanner import run_alert_scan


def _seed_empresa_concentrada(db, *, n_contratos, monto_cada_uno, institution_id=1):
    comp = Company(nombre="Constructora Concentrada SRL", rnc="111111111")
    db.add(comp)
    db.commit()
    for i in range(n_contratos):
        db.add(Contract(
            numero_contrato=f"CC-{i}", company_id=comp.id, institution_id=institution_id,
            modalidad="comparacion_precios", monto_original=monto_cada_uno,
            moneda="DOP", estado=ContractStatus.VIGENTE,
        ))
    db.commit()
    return comp


def test_no_genera_alerta_si_monto_total_es_bajo(db_session):
    # 25 contratos (cruza cnt>=20) pero de RD$100K cada uno = RD$2.5M total,
    # muy por debajo del umbral de materialidad RD$20M
    _seed_empresa_concentrada(db_session, n_contratos=25, monto_cada_uno=100_000)

    nuevas = run_alert_scan(db_session)

    assert not any(a.tipo == AlertType.EMPRESA_CONCENTRADA for a in nuevas)


def test_genera_una_sola_alerta_con_monto_material(db_session):
    # 25 contratos de RD$1M = RD$25M total, cruza cnt>=20 Y monto>=20M
    _seed_empresa_concentrada(db_session, n_contratos=25, monto_cada_uno=1_000_000)

    nuevas = run_alert_scan(db_session)

    concentradas = [a for a in nuevas if a.tipo == AlertType.EMPRESA_CONCENTRADA]
    assert len(concentradas) == 1


def test_correr_dos_veces_no_duplica(db_session):
    _seed_empresa_concentrada(db_session, n_contratos=25, monto_cada_uno=1_000_000)

    run_alert_scan(db_session)
    segunda = run_alert_scan(db_session)

    assert not any(a.tipo == AlertType.EMPRESA_CONCENTRADA for a in segunda)
    assert db_session.query(Alert).filter(Alert.tipo == AlertType.EMPRESA_CONCENTRADA).count() == 1
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `cd backend && python -m pytest tests/test_alert_scanner_empresa_concentrada.py -v`
Expected: FAIL en `test_no_genera_alerta_si_monto_total_es_bajo` (hoy genera alerta con solo `cnt>=20`, sin filtro de monto) y en `test_correr_dos_veces_no_duplica` (el bug de dedup crea una segunda fila)

- [ ] **Step 4: Implementar el fix**

En `backend/app/services/alert_scanner.py`, reemplazar la regla 4 completa (líneas 68-87):

```python
    # 4. Empresas con >20 contratos en misma institución
    rows = db.query(
        Contract.company_id, Contract.institution_id,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto"),
    ).group_by(Contract.company_id, Contract.institution_id)\
     .having(func.count(Contract.id) >= settings.ALERT_COMPANY_CONTRACT_COUNT).all()
    for r in rows:
        comp = db.query(Company).get(r.company_id)
        key = r.company_id * 100000 + r.institution_id
        if comp and not _alert_exists(db, AlertType.EMPRESA_CONCENTRADA, key):
            nuevas.append(_add(db, Alert(
                tipo=AlertType.EMPRESA_CONCENTRADA,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Empresa con {r.cnt} contratos en misma institución",
                descripcion=f"{comp.nombre} tiene {r.cnt} contratos totalizando {_fmt(r.monto)}",
                entidad_tipo="empresa", entidad_id=r.company_id,
                monto_involucrado=r.monto,
                datos_extra={},
            )))
```

por:

```python
    # 4. Empresas con >20 contratos en misma institución Y monto material
    #    (>= RD$20M) — sin el filtro de monto, esta regla generaba 26,490
    #    alertas (78% del total, ver spec §3.3); calibrado con SQL directo
    #    contra la BD real: cnt>=20 solo = 5,298 grupos, cnt>=20 + monto
    #    material = 466. La deduplicación además tenía un bug: chequeaba
    #    existencia con una clave compuesta (company*100000+institution)
    #    pero guardaba entidad_id=company_id sin componer, así que
    #    `_alert_exists` nunca encontraba coincidencia real y cada corrida
    #    volvía a crear la misma alerta (una empresa llegó a acumular 410
    #    duplicados). Ahora se construye el set de pares ya alertados UNA
    #    vez, leyendo institution_id desde datos_extra.
    ya_alertadas = {
        (a.entidad_id, (a.datos_extra or {}).get("institution_id"))
        for a in db.query(Alert).filter(
            Alert.tipo == AlertType.EMPRESA_CONCENTRADA, Alert.descartada == False,
        ).all()
    }
    rows = db.query(
        Contract.company_id, Contract.institution_id,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto"),
    ).group_by(Contract.company_id, Contract.institution_id)\
     .having(
        func.count(Contract.id) >= settings.ALERT_COMPANY_CONTRACT_COUNT,
        func.sum(Contract.monto_original) >= settings.ALERT_CONCENTRACION_MIN_MONTO,
     ).all()
    for r in rows:
        comp = db.query(Company).get(r.company_id)
        par = (r.company_id, r.institution_id)
        if comp and par not in ya_alertadas:
            nuevas.append(_add(db, Alert(
                tipo=AlertType.EMPRESA_CONCENTRADA,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Empresa con {r.cnt} contratos en misma institución",
                descripcion=f"{comp.nombre} tiene {r.cnt} contratos totalizando {_fmt(r.monto)}",
                entidad_tipo="empresa", entidad_id=r.company_id,
                monto_involucrado=r.monto,
                datos_extra={"institution_id": r.institution_id},
            )))
            ya_alertadas.add(par)
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `cd backend && python -m pytest tests/test_alert_scanner_empresa_concentrada.py -v`
Expected: `3 passed`

- [ ] **Step 6: Correr TODA la suite para verificar que nada se rompió**

Run: `cd backend && python -m pytest tests/ -v`
Expected: todos los tests de Tasks 2-12 en verde.

- [ ] **Step 7: Limpieza de las 26,490 filas duplicadas ya existentes en la BD real**

Este paso toca datos reales, no solo tests — correr una sola vez, a mano, con backup primero:

```bash
cd /Users/branel/Desktop/GOB.DO/backend
cp govtracker_test.db govtracker_test.db.backup-antes-de-limpieza-dedup
python3 -c "
import sqlite3
conn = sqlite3.connect('govtracker_test.db')
cur = conn.cursor()
# Conserva solo la fila MÁS ANTIGUA por entidad_id (company_id) — no se
# puede reconstruir el par (empresa, institución) real de las filas viejas
# porque nunca guardaron institution_id en datos_extra (regla anterior:
# datos_extra={}). Colapsar por company_id es honesto: no inventa qué
# institución era, solo elimina duplicados exactos.
cur.execute('''
    DELETE FROM alertas
    WHERE tipo = 'EMPRESA_CONCENTRADA'
    AND id NOT IN (
        SELECT MIN(id) FROM alertas WHERE tipo = 'EMPRESA_CONCENTRADA' GROUP BY entidad_id
    )
''')
print('Filas eliminadas:', cur.rowcount)
conn.commit()
conn.close()
"
```

Expected: imprime algo cercano a `Filas eliminadas: 24260` (26,490 − 2,230 distintas).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/alert_scanner.py backend/app/core/config.py backend/tests/test_alert_scanner_empresa_concentrada.py
git commit -m "$(cat <<'EOF'
fix: EMPRESA_CONCENTRADA — arregla bug de deduplicación y exige monto material

Bug real verificado con SQL: _alert_exists comparaba con una clave
compuesta que nunca coincidía con lo guardado (entidad_id=company_id
plano), así que cada corrida duplicaba la alerta. Una empresa acumuló
410 filas idénticas. Se limpiaron 24,260 duplicados de la BD real
(backup en govtracker_test.db.backup-antes-de-limpieza-dedup).

Umbral: cnt>=20 sin filtro de monto = 5,298 grupos. Con monto material
(>=RD$20M, ALERT_CONCENTRACION_MIN_MONTO) = 466. Ambos números vienen
de consultar la BD real, no de estimación.
EOF
)"
```

**No commitear** `govtracker_test.db` ni el `.backup` (ambos en `.gitignore` vía `backend/*.db`) — solo el código.

---

### Task 13: Verificación real de Telegram (bloqueada por credenciales del usuario)

**Files:** Ninguno — verificación manual, no código.

**Precondición:** el usuario generó el bot con @BotFather (nombres sugeridos: `govtrackerrd_investigador_bot`, `gobdo_alertas_bot`, `investigador_rd2026_bot`) y tiene `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (vía @userinfobot).

- [ ] **Step 1: Configurar secretos en GitHub**

```bash
gh secret set TELEGRAM_BOT_TOKEN --repo <usuario>/govtracker-rd
gh secret set TELEGRAM_CHAT_ID --repo <usuario>/govtracker-rd
```

(cada comando pide pegar el valor de forma interactiva — no pasar el valor en texto plano por la CLI en el historial de shell)

- [ ] **Step 2: Configurar también en el `.env` local para probar antes del cron**

Agregar a `backend/.env` (nunca se commitea):
```
TELEGRAM_BOT_TOKEN=<el token real>
TELEGRAM_CHAT_ID=<el chat id real>
```

- [ ] **Step 3: Enviar un mensaje real y CONFIRMAR que llegó**

Run:
```bash
cd backend && python -c "
from app.services.notifier import TelegramNotifier
import os
n = TelegramNotifier(os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID'])
n.send('Prueba real del investigador GovTracker — si ves esto, funciona.')
print('enviado sin excepción')
"
```

**Este paso no se da por completo hasta que el usuario confirme en el chat de Telegram que el mensaje llegó.** Coherente con la lección del mismo día en `armario-virtual`: HTTP 200 no es verificación, el mensaje visible en el teléfono sí lo es.

- [ ] **Step 4: Disparar el workflow completo end-to-end**

Run: `gh workflow run investigar.yml && gh run watch`
Expected: corrida verde, y un mensaje de Telegram real si `alert_scanner` encontró algo nuevo (probablemente nada en la segunda corrida del día, ya que Task 12 limpió los duplicados y la mayoría de patrones ya están alertados — es sano que no llegue nada, confirma que el diff funciona).

---

## Self-Review

**Cobertura del spec:** Fase 0 (Tasks 0-2) ✅, Fase 1 (Tasks 3-4, 9) ✅, Fase 2 (Tasks 5-8, 13; Gmail con código listo pero sin activar, decisión explícita del usuario) ✅, Fase 3 (Tasks 10-12: cédula, consolidar doble-cobro, arreglar+calibrar EMPRESA_CONCENTRADA con datos reales, auditar PROVEEDOR_INHABILITADO) ✅. Fase 3.4 (reglas de cruce nuevas: `IMPUTADO_CONTRATISTA`, `GASTO_SIN_CONTRATO`, `REPRESENTANTE_MULTI_EMPRESA`) y Fases 4-5 quedan fuera — el propio spec las marca "solo tras 3.1-3.3" y "posterior".

**Placeholders:** ninguno — cada test tiene aserciones concretas, cada implementación es código completo, los umbrales vienen de consultas SQL reales documentadas en el propio task.

**Consistencia de tipos:** `SourceResult`/`DailySource` (Task 3) se usan igual en Task 8. `get_new_alerts`/`build_digest`/`get_notifiers` (Tasks 5-7) se importan con la misma firma en Task 8. `AlertType.NOMINA_DOBLE_COBRO` se agrega en Task 11 antes de usarse.

**Orden de dependencia para dispatch paralelo (si se usa subagent-driven-development):** Task 0 → Task 1 y Task 2 pueden ir en paralelo tras Task 0. Tasks 3, 5, 6, 7 son independientes entre sí (todas solo dependen de Task 2) y se pueden dispatchar en paralelo. Task 4 depende solo de Task 2. Task 8 depende de 3+5+6+7. Task 9 depende de 8. Tasks 10, 11, 12 son independientes entre sí y de 3-9 (todas solo dependen de Task 2) — se pueden dispatchar en paralelo con el bloque 3/5/6/7. Task 13 depende de 8 y 9, y de que el usuario tenga las credenciales.
