from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import asyncio
import os
import tempfile
from loguru import logger
from ...core.config import settings
from ...core.database import get_db, SessionLocal
from ...etl.pipeline import ETLPipeline
from ...etl.parsers.pdf_parser import PDFParser, ExcelParser
from ...models.etl_run import EtlRun

router = APIRouter(prefix="/etl", tags=["ETL / Scraping"])

_pipeline_status = {"running": False, "last_run": None, "last_result": None}
_deteccion_temprana_status = {"running": False}


@router.post("/seed/punta-catalina")
async def seed_punta_catalina():
    """Siembra todos los datos documentados del caso Punta Catalina."""
    from ...etl.scrapers.punta_catalina_seed import seed_punta_catalina as _seed
    result = await _seed()
    return {"status": "ok", "resultado": result}


@router.post("/seed/combustibles")
async def seed_combustibles():
    """Siembra el sector Combustibles / PANAM (gasolina, conflictos de interés)."""
    from ...etl.scrapers.combustibles_scraper import run_combustibles_scraper
    count = await run_combustibles_scraper()
    return {"status": "ok", "registros": count}


@router.post("/seed/seguros-senasa")
async def seed_seguros_senasa():
    """Siembra el sector Seguros / SENASA (ARS, aseguradoras, SISALRIL)."""
    from ...etl.scrapers.seguros_senasa_scraper import run_seguros_senasa_scraper
    count = await run_seguros_senasa_scraper()
    return {"status": "ok", "registros": count}


@router.post("/scrape/pgr")
async def scrape_pgr(
    background_tasks: BackgroundTasks,
    max_pages: int = Query(100, ge=1, le=991, description="Páginas a scrapear (9 arts/pág)"),
    incremental: bool = Query(True, description="Para al encontrar URLs ya almacenadas"),
):
    """
    Scraper de comunicados oficiales de la Procuraduría General de la República (pgr.gob.do).
    Extrae título, cuerpo, fecha, tipo, operación, montos e imputados mencionados.
    Corre en background. Estado en /etl/scrape/pgr/status
    """
    background_tasks.add_task(_run_pgr_scraper_bg, max_pages, incremental)
    return {
        "status": "started",
        "message": f"Scraping PGR — hasta {max_pages} páginas (~{max_pages * 9} artículos), incremental={incremental}",
    }


_pgr_status: dict = {"running": False, "saved": 0, "errors": 0, "last_run": None}


async def _run_pgr_scraper_bg(max_pages: int, incremental: bool):
    from ...etl.scrapers.pgr_scraper import run_pgr_scraper
    _pgr_status["running"] = True
    try:
        count = await run_pgr_scraper(max_pages=max_pages, incremental=incremental)
        _pgr_status["saved"] = count
        _pgr_status["last_run"] = "ok"
    except Exception as e:
        _pgr_status["last_run"] = f"error: {e}"
    finally:
        _pgr_status["running"] = False


@router.get("/scrape/pgr/status")
def pgr_scraper_status():
    """Estado del scraper PGR y estadísticas de la BD."""
    from pathlib import Path
    import sqlite3
    db_path = Path(__file__).parent.parent.parent.parent / "data" / "pgr.db"
    stats = {"total": 0, "por_tipo": {}, "operaciones": [], "con_fecha": 0}
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        stats["total"] = conn.execute("SELECT COUNT(*) FROM comunicados").fetchone()[0]
        stats["con_fecha"] = conn.execute(
            "SELECT COUNT(*) FROM comunicados WHERE fecha IS NOT NULL"
        ).fetchone()[0]
        stats["por_tipo"] = {
            r["tipo"]: r["cnt"]
            for r in conn.execute(
                "SELECT tipo, COUNT(*) AS cnt FROM comunicados GROUP BY tipo ORDER BY cnt DESC"
            ).fetchall()
        }
        stats["operaciones"] = [
            r["operacion"]
            for r in conn.execute(
                "SELECT DISTINCT operacion FROM comunicados WHERE operacion IS NOT NULL ORDER BY operacion"
            ).fetchall()
        ]
        conn.close()
    return {**_pgr_status, "db_stats": stats}


@router.post("/seed/seguridad")
async def seed_seguridad():
    """Siembra el sector Policía / Bomberos / instituciones de seguridad."""
    from ...etl.scrapers.seguridad_scraper import run_seguridad_scraper
    count = await run_seguridad_scraper()
    return {"status": "ok", "registros": count}


@router.post("/seed/map-nominas")
async def seed_map_nominas(
    background_tasks: BackgroundTasks,
    anio: int = Query(..., description="Año a importar, ej. 2026"),
    meses: Optional[List[int]] = Query(None, description="Meses 1-12; por defecto todo el año"),
):
    """
    Importa nómina de MOPC, Ministerio de Educación y Servicio Nacional de
    Salud desde el dataset centralizado de MAP (map.gob.do/datosabiertos) —
    las 3 instituciones grandes que faltaban en las 90 ya cubiertas por
    scrapers individuales en data/nominas.db. Corre en background porque cada
    mes descarga un CSV de ~60MB con la nómina completa de gobierno central.
    """
    background_tasks.add_task(_run_map_nominas_bg, anio, meses)
    return {"status": "started", "message": f"Importando nómina MAP {anio} en background"}


async def _run_map_nominas_bg(anio: int, meses: Optional[List[int]]):
    from ...etl.scrapers.map_nominas_scraper import run_map_nominas_scraper
    try:
        result = await run_map_nominas_scraper(anio, meses)
        logger.info(f"MAP nóminas {anio} completado: {result}")
    except Exception as e:
        logger.error(f"MAP nóminas {anio} falló: {e}")


@router.post("/seed/camara-diputados")
async def seed_camara_diputados():
    """Sincroniza Cámara de Diputados / Senado desde la API en vivo del SIL (diputadosrd.gob.do)."""
    from ...etl.scrapers.camara_diputados_scraper import run_camara_diputados_scraper
    count = await run_camara_diputados_scraper()
    return {"status": "ok", "registros": count}


@router.post("/seed/congreso-comisiones")
async def seed_congreso_comisiones():
    """Sincroniza comisiones del Congreso (mesa directiva, permanentes, especiales) desde el SIL en vivo."""
    from ...etl.scrapers.congreso_comisiones_scraper import run_congreso_comisiones_scraper
    count = await run_congreso_comisiones_scraper()
    return {"status": "ok", "registros": count}


@router.get("/dgii/rnc/{rnc}")
async def consultar_rnc(rnc: str):
    """Consulta datos de un RNC directamente en la DGII (tiempo real)."""
    from ...etl.scrapers.dgii_scraper import enrich_company_by_rnc
    data = await enrich_company_by_rnc(rnc)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(404, f"RNC {rnc} no encontrado en DGII")
    return data


@router.post("/dgii/enrich")
async def enrich_all_companies(
    background_tasks: BackgroundTasks,
    limit: int = Query(200, le=1000),
):
    """Enriquece todas las empresas con datos de DGII (representante legal, actividad)."""
    background_tasks.add_task(_run_dgii_enrichment, limit)
    return {"status": "started", "message": f"Enriqueciendo hasta {limit} empresas con DGII"}


async def _run_dgii_enrichment(limit: int):
    from ...etl.scrapers.dgii_scraper import run_dgii_scraper
    await run_dgii_scraper(limit)


@router.post("/run")
async def run_etl(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(None),
):
    if _pipeline_status["running"]:
        return {"status": "already_running", "message": "Pipeline ya está en ejecución"}
    background_tasks.add_task(_run_pipeline, sources)
    return {"status": "started", "message": "Pipeline ETL iniciado en background"}


@router.get("/status")
def etl_status():
    return _pipeline_status


@router.post("/deteccion-temprana")
async def run_deteccion_temprana(
    background_tasks: BackgroundTasks,
    descargar: bool = Query(True, description="Descargar los CSV oficiales más recientes de DGCP antes de importar"),
):
    """
    Pipeline de detección temprana, todo en una sola llamada:
    1. Descarga los datasets oficiales más recientes de DGCP (proveedores,
       adjudicaciones, procesos, inhabilitados) — solo agrega lo nuevo.
    2. Refresca el cruce legislador ↔ representante legal de empresa contratista.
    3. Corre el scanner de alertas sobre los datos actualizados.

    El objetivo es que un mismo disparo (manual hoy; programable con cron/
    scheduler cuando esto esté desplegado) detecte conflictos de interés o
    patrones sospechosos en contratos recién publicados, en vez de depender
    de que alguien note la noticia primero y luego alguien dispare cada paso
    de scraping/scan por separado.
    """
    if _deteccion_temprana_status["running"]:
        return {"status": "already_running", "message": "La detección temprana ya está en ejecución"}
    background_tasks.add_task(_run_deteccion_temprana_bg, descargar)
    return {"status": "started", "message": "Detección temprana iniciada en background"}


async def _run_deteccion_temprana_bg(descargar: bool):
    from ...etl.scrapers.dgcp_bulk_importer import run_dgcp_bulk_import
    from ...etl.scrapers.camara_diputados_scraper import run_camara_diputados_scraper
    from ...services.alert_scanner import run_alert_scan

    _deteccion_temprana_status["running"] = True
    db = SessionLocal()
    run = EtlRun(fuente="deteccion_temprana", estado="ok")
    db.add(run)
    db.commit()
    detalle: dict = {}
    try:
        detalle["dgcp"] = run_dgcp_bulk_import(descargar=descargar)

        try:
            n_legisladores = await run_camara_diputados_scraper()
            detalle["camara_diputados"] = {"status": "ok", "registros": n_legisladores}
        except Exception as e:
            logger.warning(f"Detección temprana: falló refresh de Cámara de Diputados: {e}")
            detalle["camara_diputados"] = {"status": "error", "error": str(e)}

        nuevas_alertas = run_alert_scan(db)
        detalle["alertas_nuevas"] = [
            {
                "tipo": a.tipo.value, "severidad": a.severidad.value,
                "titulo": a.titulo, "monto_involucrado": a.monto_involucrado,
            }
            for a in nuevas_alertas
        ]

        run.estado = "ok"
        run.registros_nuevos = (detalle["dgcp"].get("contratos", 0) or 0) + (detalle["dgcp"].get("proveedores", 0) or 0)
        run.alertas_nuevas = len(nuevas_alertas)
        run.detalle = detalle
        run.finalizado_en = datetime.utcnow()
        db.commit()
        _pipeline_status["last_result"] = detalle
        _pipeline_status["last_run"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.error(f"Detección temprana falló: {e}")
        run.estado = "error"
        run.error = str(e)
        run.detalle = detalle
        run.finalizado_en = datetime.utcnow()
        db.commit()
    finally:
        db.close()
        _deteccion_temprana_status["running"] = False


@router.get("/runs")
def list_etl_runs(db: Session = Depends(get_db), limit: int = Query(20, le=100)):
    """Historial real de corridas ETL — responde 'cada cuánto se actualiza'
    con datos persistidos en vez del estado en memoria que se perdía al
    reiniciar el servidor."""
    runs = db.query(EtlRun).order_by(EtlRun.iniciado_en.desc()).limit(limit).all()
    return [
        {
            "id": r.id, "fuente": r.fuente, "estado": r.estado,
            "iniciado_en": r.iniciado_en.isoformat() if r.iniciado_en else None,
            "finalizado_en": r.finalizado_en.isoformat() if r.finalizado_en else None,
            "registros_nuevos": r.registros_nuevos, "alertas_nuevas": r.alertas_nuevas,
            "detalle": r.detalle, "error": r.error,
        }
        for r in runs
    ]


@router.post("/upload/contracts")
async def upload_contracts_file(file: UploadFile = File(...)):
    """Sube un archivo Excel/CSV de contratos para importar."""
    content = await file.read()
    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if suffix in (".xlsx", ".xls"):
            parser = ExcelParser()
            records = parser.parse_contracts_excel(tmp_path)
        elif suffix == ".csv":
            parser = ExcelParser()
            records = parser.parse_budget_csv(tmp_path)
        else:
            return {"error": f"Formato no soportado: {suffix}"}
        # Aquí se procesarían los records
        return {"status": "ok", "records_parsed": len(records), "sample": records[:3]}
    finally:
        os.unlink(tmp_path)


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Extrae texto y campos de un PDF de contrato o auditoría."""
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        parser = PDFParser()
        text = parser.extract_text(tmp_path)
        if not text:
            return {"error": "No se pudo extraer texto del PDF"}
        contract_data = parser.extract_contract_data(text)
        audit_findings = parser.extract_audit_findings(text)
        return {
            "filename": file.filename,
            "text_length": len(text),
            "text_preview": text[:500],
            "contract_data": contract_data,
            "audit_findings": audit_findings,
        }
    finally:
        os.unlink(tmp_path)


async def _run_pipeline(sources):
    _pipeline_status["running"] = True
    try:
        pipeline = ETLPipeline()
        result = await pipeline.run_full(sources)
        _pipeline_status["last_result"] = result
        from datetime import datetime
        _pipeline_status["last_run"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        _pipeline_status["last_result"] = {"error": str(e)}
    finally:
        _pipeline_status["running"] = False
