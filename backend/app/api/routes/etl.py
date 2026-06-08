from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Query
from typing import Optional, List
import asyncio
import os
import tempfile
from loguru import logger
from ...core.config import settings
from ...etl.pipeline import ETLPipeline
from ...etl.parsers.pdf_parser import PDFParser, ExcelParser

router = APIRouter(prefix="/etl", tags=["ETL / Scraping"])

_pipeline_status = {"running": False, "last_run": None, "last_result": None}


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


@router.post("/seed/seguridad")
async def seed_seguridad():
    """Siembra el sector Policía / Bomberos / instituciones de seguridad."""
    from ...etl.scrapers.seguridad_scraper import run_seguridad_scraper
    count = await run_seguridad_scraper()
    return {"status": "ok", "registros": count}


@router.post("/seed/camara-diputados")
async def seed_camara_diputados():
    """Sincroniza Cámara de Diputados / Senado desde la API en vivo del SIL (diputadosrd.gob.do)."""
    from ...etl.scrapers.camara_diputados_scraper import run_camara_diputados_scraper
    count = await run_camara_diputados_scraper()
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
