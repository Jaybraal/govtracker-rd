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


class ETLPipeline:

    async def run_full(self, sources: list = None):
        """Ejecuta pipeline completo o subconjunto de fuentes."""
        sources = sources or [
            "hacienda", "credito_publico", "idecoop", "sib", "jce",
            "combustibles", "seguros_senasa", "seguridad",
            "camara_diputados", "congreso_comisiones", "dgcp",
        ]
        logger.info(f"Pipeline ETL iniciado: {sources}")
        results = {}

        # 1. Hacienda primero (seed de instituciones base)
        if "hacienda" in sources:
            try:
                count = await run_hacienda_scraper()
                results["hacienda"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Hacienda pipeline error: {e}")
                results["hacienda"] = {"status": "error", "error": str(e)}

        # 2. Crédito Público (préstamos)
        if "credito_publico" in sources:
            try:
                count = await run_credito_publico_scraper()
                results["credito_publico"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Crédito Público pipeline error: {e}")
                results["credito_publico"] = {"status": "error", "error": str(e)}

        # 3. IDECOOP (cooperativas)
        if "idecoop" in sources:
            try:
                count = await run_idecoop_scraper()
                results["idecoop"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"IDECOOP pipeline error: {e}")
                results["idecoop"] = {"status": "error", "error": str(e)}

        # 4. SIB — bancos
        if "sib" in sources:
            try:
                count = await run_sib_scraper()
                results["sib"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"SIB pipeline error: {e}")
                results["sib"] = {"status": "error", "error": str(e)}

        # 5. JCE — partidos políticos
        if "jce" in sources:
            try:
                count = await run_jce_scraper()
                results["jce"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"JCE pipeline error: {e}")
                results["jce"] = {"status": "error", "error": str(e)}

        # 6. Combustibles / PANAM (sector gasolina, conflictos de interés)
        if "combustibles" in sources:
            try:
                count = await run_combustibles_scraper()
                results["combustibles"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Combustibles pipeline error: {e}")
                results["combustibles"] = {"status": "error", "error": str(e)}

        # 7. Seguros y SENASA (sector salud / seguros)
        if "seguros_senasa" in sources:
            try:
                count = await run_seguros_senasa_scraper()
                results["seguros_senasa"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Seguros/SENASA pipeline error: {e}")
                results["seguros_senasa"] = {"status": "error", "error": str(e)}

        # 8. Policía, Bomberos e instituciones de seguridad
        if "seguridad" in sources:
            try:
                count = await run_seguridad_scraper()
                results["seguridad"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Seguridad pipeline error: {e}")
                results["seguridad"] = {"status": "error", "error": str(e)}

        # 9. Cámara de Diputados / Senado (legisladores — SIL, ETL en vivo)
        if "camara_diputados" in sources:
            try:
                count = await run_camara_diputados_scraper()
                results["camara_diputados"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Cámara de Diputados pipeline error: {e}")
                results["camara_diputados"] = {"status": "error", "error": str(e)}

        # 9b. Comisiones del Congreso (mesa directiva, comisiones permanentes — SIL, ETL en vivo)
        if "congreso_comisiones" in sources:
            try:
                count = await run_congreso_comisiones_scraper()
                results["congreso_comisiones"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"Comisiones del Congreso pipeline error: {e}")
                results["congreso_comisiones"] = {"status": "error", "error": str(e)}

        # 10. DGCP (contratos) — más pesado, al final
        if "dgcp" in sources:
            try:
                count = await run_dgcp_scraper(max_pages=50)
                results["dgcp"] = {"status": "ok", "records": count}
            except Exception as e:
                logger.error(f"DGCP pipeline error: {e}")
                results["dgcp"] = {"status": "error", "error": str(e)}

        logger.info(f"Pipeline ETL completado: {results}")
        return results

    async def run_incremental(self):
        """Solo actualiza datos nuevos desde última ejecución."""
        return await self.run_full()


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
