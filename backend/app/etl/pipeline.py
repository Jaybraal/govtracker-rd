"""
Pipeline ETL central — orquesta todos los scrapers y actualiza la BD.
"""
import asyncio
from datetime import datetime
from loguru import logger
from .scrapers.dgcp_scraper import run_dgcp_scraper
from .scrapers.hacienda_scraper import run_hacienda_scraper
from .scrapers.credito_publico_scraper import run_credito_publico_scraper
from .scrapers.idecoop_scraper import run_idecoop_scraper
from .scrapers.sib_scraper import run_sib_scraper
from .scrapers.jce_scraper import run_jce_scraper
from .scrapers.combustibles_scraper import run_combustibles_scraper
from .scrapers.seguros_senasa_scraper import run_seguros_senasa_scraper
from .scrapers.seguridad_scraper import run_seguridad_scraper
from .scrapers.camara_diputados_scraper import run_camara_diputados_scraper
from .scrapers.congreso_comisiones_scraper import run_congreso_comisiones_scraper
from .scrapers.dgcp_bulk_importer import run_dgcp_bulk_import
from .scrapers.hacienda_ejecucion_importer import run_import as run_hacienda_ejecucion_import
from .scrapers.diputados_nominas_scraper import run_diputados_nominas_scraper
from .scrapers.map_nominas_scraper import run_map_nominas_scraper
from .scrapers.pgr_nominas_scraper import run_pgr_nominas_scraper
from .scrapers.pgr_scraper import run_pgr_scraper
from .scrapers.dgii_scraper import run_dgii_scraper


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


# Celery tasks
try:
    from celery import Celery
    from ..core.config import settings
    celery_app = Celery("govtracker", broker=settings.CELERY_BROKER_URL,
                        backend=settings.CELERY_RESULT_BACKEND)

    @celery_app.task(name="etl.run_full")
    def task_run_full(sources=None):
        return asyncio.run(ETLPipeline().run_full(sources))

    @celery_app.task(name="etl.run_incremental")
    def task_run_incremental():
        return asyncio.run(ETLPipeline().run_incremental())

except ImportError:
    pass
