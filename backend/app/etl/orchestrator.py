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
