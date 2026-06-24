"""
Cámara de Diputados / Senado — Congreso Nacional de la República Dominicana.

ETL en vivo (sin datos sembrados — igual patrón que `dgcp_scraper.py` /
`idecoop_scraper.py`): consume directamente la API pública del Sistema de
Información Legislativa (SIL), el sistema oficial de la Cámara de Diputados.

──────────────────────────────────────────────────────────────────────────────
ORIGEN DEL ENDPOINT (investigación 2026-06-07)
──────────────────────────────────────────────────────────────────────────────
El SIL (https://www.diputadosrd.gob.do/sil/) es una SPA en Angular sobre una
API REST ASP.NET. El endpoint de listado de legisladores se localizó
descargando el bundle de Angular (`Script/Bundles?v=...`) y leyendo la
definición de `getLegisladoresByKeyword`:

    GET https://www.diputadosrd.gob.do/sil/api/legislador/legisladores
        ?page=<N>&keyword=<letra>

Paginado de a 10 resultados (`pageSize`); con `keyword` igual a cualquier
vocal (a/e/i/o/u) el total reportado es 225 — la cifra estable y máxima
observada (se probó también con consonantes: "z" devuelve 149, "x" devuelve
20 — subconjuntos), por lo que `keyword="a"` recorre el universo completo de
legisladores. El campo `funcion` distingue Diputado/Diputada, Senador/
Senadora e "Institución del Estado" (escaños institucionales sin titular
individual, que se omiten aquí).

Recuento en vivo verificado el 2026-06-07: 190 Diputados + 32 Senadores
(222 personas + 3 registros institucionales = 225 total).

Fuente: Cámara de Diputados de la República Dominicana — Sistema de
Información Legislativa (SIL), https://www.diputadosrd.gob.do/sil/
(API oficial, consulta en vivo — institución pública, no intermediario
periodístico).
"""
import asyncio
import httpx
from datetime import datetime
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from ...core.config import settings
from ...core.database import SessionLocal
from ...models.legislator import Legislator, LegislatorChamber
from ...models.institution import Institution, InstitutionType
from ...models.company import LegalRepresentative
from ...models.contract import Contract
from sqlalchemy import func


SIL_BASE_URL = "https://www.diputadosrd.gob.do/sil/api/legislador"
_FUENTE = "Cámara de Diputados — Sistema de Información Legislativa (SIL), consulta en vivo"
_URL_FUENTE = "https://www.diputadosrd.gob.do/sil/"

_FUNCION_CAMARA = {
    "diputado":  LegislatorChamber.DIPUTADOS,
    "diputada":  LegislatorChamber.DIPUTADOS,
    "senador":   LegislatorChamber.SENADO,
    "senadora":  LegislatorChamber.SENADO,
}

INSTITUCIONES_CONGRESO = [
    ("CD",     "Cámara de Diputados de la República Dominicana", InstitutionType.CONGRESO),
    ("SENADO", "Senado de la República Dominicana",              InstitutionType.CONGRESO),
]


class CamaraDiputadosScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper Cámara de Diputados / Senado (SIL — ETL en vivo)...")
        await self._seed_instituciones()
        count = await self._scrape_legisladores()
        await self._cruzar_con_contratos()
        self.db.close()
        logger.info(f"Cámara de Diputados/Senado: {count} legisladores sincronizados desde el SIL")
        return count

    async def _seed_instituciones(self):
        for siglas, nombre, tipo in INSTITUCIONES_CONGRESO:
            if not self.db.query(Institution).filter(Institution.siglas == siglas).first():
                self.db.add(Institution(codigo=f"INST-{siglas}", nombre=nombre, siglas=siglas, tipo=tipo))
        self.db.commit()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> dict:
        resp = await client.get(
            f"{SIL_BASE_URL}/legisladores",
            params={"page": page, "keyword": "a"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _scrape_legisladores(self) -> int:
        count = 0
        try:
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True,
                headers={"User-Agent": settings.USER_AGENT},
            ) as client:
                page = 1
                total = None
                while total is None or (page - 1) * 10 < total:
                    data = await self._fetch_page(client, page)
                    total = data.get("total", 0)
                    results = data.get("results", [])
                    if not results:
                        break
                    for item in results:
                        if self._upsert_legislador(item):
                            count += 1
                    self.db.commit()
                    logger.info(f"SIL página {page}: {len(results)} legisladores procesados (total reportado: {total})")
                    page += 1
                    await asyncio.sleep(settings.SCRAPER_DELAY)
        except Exception as e:
            logger.error(f"Error consultando el SIL: {e}")
        return count

    def _upsert_legislador(self, item: dict) -> bool:
        funcion = (item.get("funcion") or "").strip()
        camara = _FUNCION_CAMARA.get(funcion.lower())
        if camara is None:
            # "Institución del Estado" u otros valores no individuales — se omite
            return False

        legislador_id = item.get("legisladorId")
        nombre_completo = item.get("nombreCompleto")
        if not nombre_completo:
            return False

        existing = None
        if legislador_id is not None:
            existing = self.db.query(Legislator).filter(Legislator.legislador_id_sil == legislador_id).first()
        if not existing:
            existing = self.db.query(Legislator).filter(
                Legislator.nombre_completo == nombre_completo,
                Legislator.camara == camara,
            ).first()

        partido = item.get("partido") or {}
        values = dict(
            legislador_id_sil=legislador_id,
            nombre_completo=nombre_completo,
            camara=camara,
            funcion=funcion,
            partido_siglas=partido.get("siglas"),
            partido_nombre=partido.get("nombre"),
            provincia=item.get("provincia"),
            circunscripcion=item.get("circunscripcion"),
            fuente=_FUENTE,
            url_fuente=_URL_FUENTE,
            raw_data=item,
        )

        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            return False

        self.db.add(Legislator(**values))
        self.db.flush()
        return True

    async def _cruzar_con_contratos(self):
        """
        Detección de conflicto de interés: ¿el nombre completo de algún
        legislador en ejercicio coincide con el de un representante legal
        registrado de una empresa contratista del Estado?

        Mismo patrón que `IdecoopScraper._cruzar_con_contratos` — cruce por
        coincidencia textual de nombre, sin inventar relaciones. Hoy la tabla
        `representantes_legales` está casi vacía (la mayoría de empresas
        sembradas con datos reales de prensa fueron eliminadas por falta de
        fuente oficial — ver correcciones 2026-06-07 en seguridad_scraper.py /
        seguros_senasa_scraper.py); el cruce se deja activo para que opere
        automáticamente conforme el enriquecimiento DGII (`dgii_scraper.py`)
        vaya poblando representantes legales reales.
        """
        legisladores = self.db.query(Legislator).all()
        for leg in legisladores:
            # func.upper() en ambos lados — SQLite upper() es ASCII-only y no
            # uppercasea tildes minúsculas; mezclar con el .upper() de Python
            # (sí Unicode-aware) producía falsos negativos en nombres con tilde.
            reps = self.db.query(LegalRepresentative).filter(
                func.upper(LegalRepresentative.nombre) == func.upper(leg.nombre_completo)
            ).all()
            if not reps:
                leg.total_contratos_relacionados = 0
                leg.total_monto_relacionado = 0
                continue
            company_ids = {r.company_id for r in reps}
            agg = self.db.query(
                func.count(Contract.id),
                func.sum(Contract.monto_original),
            ).filter(Contract.company_id.in_(company_ids)).first()
            leg.total_contratos_relacionados = agg[0] or 0
            leg.total_monto_relacionado = agg[1] or 0
        self.db.commit()


async def run_camara_diputados_scraper():
    s = CamaraDiputadosScraper()
    return await s.run()
