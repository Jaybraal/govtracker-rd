"""
Comisiones del Congreso Nacional (Cámara de Diputados) — Sistema de
Información Legislativa (SIL), ETL en vivo.

──────────────────────────────────────────────────────────────────────────────
ORIGEN DE LOS ENDPOINTS (investigación 2026-06-10)
──────────────────────────────────────────────────────────────────────────────
Mismo SIL que `camara_diputados_scraper.py` (https://www.diputadosrd.gob.do/sil/),
localizando esta vez el servicio Angular `ComisionService` dentro del bundle
(`Script/Bundles?v=...`):

    GET https://www.diputadosrd.gob.do/sil/api/comision/tipo
        → catálogo de tipos de comisión (Permanentes, Especiales,
          Bicamerales, Coordinadora, etc.)

    GET https://www.diputadosrd.gob.do/sil/api/comision/comisiones?tipoId=<N>&page=1
        → lista completa de comisiones de ese tipo (no pagina realmente:
          siempre devuelve el total para tipoId fijo)

    GET https://www.diputadosrd.gob.do/sil/api/comision/miembros/?page=<N>&id=<comisionId>
        → miembros de la comisión, paginados de a 10, con `cargo`
          (Presidente/a, Vice-Presidente/a, Secretario/a, Miembro)

Las comisiones permanentes (tipoId=974, 52 activas) son los órganos que
estudian, dictaminan y aprueban (o rechazan) los proyectos de ley antes de
pasar al Pleno — "los que aprueban normas". La "Comisión Coordinadora"
(tipoId=978) cumple el rol de mesa directiva / agenda legislativa — "los que
convocan asambleas y toman las decisiones" (su Presidente/a es, en la
práctica, el/la Presidente/a de la Cámara de Diputados).

Recuento en vivo verificado el 2026-06-10: 52 Permanentes + 13 Especiales +
3 Bicamerales Especiales + 1 Coordinadora = 69 comisiones activas.

Fuente: Cámara de Diputados de la República Dominicana — Sistema de
Información Legislativa (SIL), https://www.diputadosrd.gob.do/sil/
(API oficial, consulta en vivo).
"""
import asyncio
import httpx
from datetime import datetime
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from ...core.config import settings
from ...core.database import SessionLocal
from ...models.commission import Commission, CommissionMember
from ...models.legislator import Legislator


SIL_COMISION_URL = "https://www.diputadosrd.gob.do/sil/api/comision"
_FUENTE = "Cámara de Diputados — Sistema de Información Legislativa (SIL), consulta en vivo"
_URL_FUENTE = "https://www.diputadosrd.gob.do/sil/"

# Catálogo fijo de `api/comision/tipo` (no cambia, pero se evita una llamada extra)
TIPOS_COMISION = {
    974: "Permanente",
    975: "Especial",
    976: "Bicameral Permanente",
    977: "Bicameral Especial",
    978: "Coordinadora",
    979: "General",
    980: "Consejo de Disciplina",
    981: "Instructora",
}


def _parse_date(s):
    if not s or str(s).startswith("0001"):
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", ""))
    except Exception:
        return None


class CongresoComisionesScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper Comisiones del Congreso (SIL — ETL en vivo)...")
        count = 0
        try:
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True,
                headers={"User-Agent": settings.USER_AGENT},
            ) as client:
                for tipo_id, tipo_label in TIPOS_COMISION.items():
                    comisiones = await self._fetch_comisiones(client, tipo_id)
                    for item in comisiones:
                        comision = self._upsert_comision(item, tipo_label)
                        self.db.commit()
                        await self._scrape_miembros(client, comision)
                        count += 1
                        await asyncio.sleep(settings.SCRAPER_DELAY)
                    logger.info(f"SIL comisiones tipoId={tipo_id} ({tipo_label}): {len(comisiones)} procesadas")
        except Exception as e:
            logger.error(f"Error consultando comisiones del SIL: {e}")
        self.db.close()
        logger.info(f"Comisiones del Congreso: {count} comisiones sincronizadas desde el SIL")
        return count

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_comisiones(self, client: httpx.AsyncClient, tipo_id: int) -> list:
        resp = await client.get(f"{SIL_COMISION_URL}/comisiones", params={"tipoId": tipo_id, "page": 1})
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_miembros_page(self, client: httpx.AsyncClient, comision_id_sil: int, page: int) -> dict:
        resp = await client.get(f"{SIL_COMISION_URL}/miembros/", params={"page": page, "id": comision_id_sil})
        resp.raise_for_status()
        return resp.json()

    def _upsert_comision(self, item: dict, tipo_label: str) -> Commission:
        comision_id_sil = item.get("id")
        existing = self.db.query(Commission).filter(Commission.comision_id_sil == comision_id_sil).first()

        values = dict(
            comision_id_sil=comision_id_sil,
            nombre=(item.get("comision") or "").strip(),
            tipo=item.get("tipo") or tipo_label,
            tipo_id_sil=item.get("tipoId"),
            descripcion=item.get("descripcion"),
            estado=item.get("estado"),
            fecha_designacion=_parse_date(item.get("fechaDesignacion")),
            fuente=_FUENTE,
            url_fuente=_URL_FUENTE,
        )

        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            return existing

        comision = Commission(**values)
        self.db.add(comision)
        self.db.flush()
        return comision

    async def _scrape_miembros(self, client: httpx.AsyncClient, comision: Commission) -> int:
        # Se reemplaza la composición completa en cada corrida para reflejar
        # el estado actual (altas/bajas de miembros, cambios de cargo).
        self.db.query(CommissionMember).filter(CommissionMember.comision_id == comision.id).delete()

        count = 0
        page = 1
        total = None
        while total is None or (page - 1) * 10 < total:
            data = await self._fetch_miembros_page(client, comision.comision_id_sil, page)
            total = data.get("total", 0)
            results = data.get("results", [])
            if not results:
                break
            for m in results:
                leg = m.get("legislador") or {}
                legislador_id_sil = leg.get("legisladorId")
                legislator = None
                if legislador_id_sil:
                    legislator = self.db.query(Legislator).filter(
                        Legislator.legislador_id_sil == legislador_id_sil
                    ).first()
                self.db.add(CommissionMember(
                    comision_id=comision.id,
                    legislator_id=legislator.id if legislator else None,
                    legislador_id_sil=legislador_id_sil,
                    nombre_completo=leg.get("nombreCompleto"),
                    partido_siglas=(m.get("partido") or {}).get("siglas"),
                    cargo=m.get("cargo"),
                    estado=m.get("estado"),
                    fecha_inicio=_parse_date(m.get("inicio")),
                    fecha_fin=_parse_date(m.get("fin")),
                ))
                count += 1
            page += 1
            await asyncio.sleep(settings.SCRAPER_DELAY)
        self.db.commit()
        return count


async def run_congreso_comisiones_scraper():
    s = CongresoComisionesScraper()
    return await s.run()
