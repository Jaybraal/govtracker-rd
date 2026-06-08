"""
DGCP (Dirección General de Contrataciones Públicas) scraper.
Fuentes: API REST + portal transaccional.
"""
import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from ...core.config import settings
from ...core.database import SessionLocal
from ...models.contract import Contract, ModalidadCompra
from ...models.company import Company
from ...models.institution import Institution


MODALIDAD_MAP = {
    "Licitación Pública": ModalidadCompra.LICITACION_PUBLICA,
    "Licitación Restringida": ModalidadCompra.LICITACION_RESTRINGIDA,
    "Comparación de Precios": ModalidadCompra.COMPARACION_PRECIOS,
    "Contratación Directa": ModalidadCompra.CONTRATACION_DIRECTA,
    "Subasta Inversa": ModalidadCompra.SUBASTA_INVERSA,
    "Sorteo de Obras": ModalidadCompra.SORTEO,
    "Acuerdo Marco": ModalidadCompra.ACUERDO_MARCO,
}


class DGCPScraper:
    """
    Scraper para la API de datos abiertos de DGCP.
    Endpoint: https://api.dgcp.gob.do/api/
    """

    BASE_URL = "https://api.dgcp.gob.do/api"

    def __init__(self):
        self.session = None
        self.db = SessionLocal()

    async def run(self, max_pages: int = 100):
        """Descarga contratos de la API DGCP paginando."""
        logger.info("Iniciando scraper DGCP...")
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        ) as client:
            page = 1
            total_imported = 0
            while page <= max_pages:
                try:
                    data = await self._fetch_page(client, page)
                    if not data or not data.get("data"):
                        logger.info(f"DGCP: fin en página {page}")
                        break
                    records = data["data"]
                    imported = await self._process_records(records)
                    total_imported += imported
                    logger.info(f"DGCP página {page}: {imported} registros importados")
                    page += 1
                    await asyncio.sleep(settings.SCRAPER_DELAY)
                except Exception as e:
                    logger.error(f"DGCP error en página {page}: {e}")
                    break

        logger.info(f"DGCP scraper completado: {total_imported} contratos importados")
        self.db.close()
        return total_imported

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> dict:
        resp = await client.get(
            f"{self.BASE_URL}/contratos",
            params={"page": page, "per_page": 100, "format": "json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _process_records(self, records: list) -> int:
        imported = 0
        for r in records:
            try:
                await self._upsert_contract(r)
                imported += 1
            except Exception as e:
                logger.warning(f"Error procesando contrato {r.get('codigo', '?')}: {e}")
        self.db.commit()
        return imported

    async def _upsert_contract(self, r: dict):
        numero = r.get("codigo_contrato") or r.get("numero_contrato") or r.get("codigo")
        if not numero:
            return

        existing = self.db.query(Contract).filter(Contract.numero_contrato == numero).first()

        # Empresa
        company = await self._get_or_create_company(r)
        # Institución
        institution = await self._get_or_create_institution(r)

        if not company or not institution:
            return

        monto = self._parse_monto(r.get("monto") or r.get("monto_contrato") or 0)
        modalidad_str = r.get("modalidad") or r.get("tipo_proceso", "")
        modalidad = MODALIDAD_MAP.get(modalidad_str, ModalidadCompra.OTRO)

        if existing:
            existing.monto_actual = monto
            existing.updated_at = datetime.utcnow()
        else:
            contract = Contract(
                numero_contrato=numero,
                numero_proceso=r.get("codigo_proceso"),
                institution_id=institution.id,
                company_id=company.id,
                descripcion=r.get("descripcion") or r.get("objeto"),
                objeto=r.get("objeto"),
                modalidad=modalidad,
                monto_original=monto,
                monto_actual=monto,
                moneda=r.get("moneda", "DOP"),
                fecha_firma=self._parse_date(r.get("fecha_contrato") or r.get("fecha_firma")),
                oficial_firmante=r.get("funcionario_firmante"),
                es_mayor_100m=monto >= 100_000_000,
                fuente="DGCP API",
                url_fuente=f"{self.BASE_URL}/contratos/{numero}",
                raw_data=r,
            )
            self.db.add(contract)

        # Actualizar contadores de empresa e institución
        self._update_company_stats(company)
        self._update_institution_stats(institution)

    async def _get_or_create_company(self, r: dict) -> Optional[Company]:
        rnc = str(r.get("rnc_proveedor") or r.get("rnc", "")).strip()
        nombre = r.get("nombre_proveedor") or r.get("proveedor", "")
        if not nombre:
            return None

        if rnc:
            comp = self.db.query(Company).filter(Company.rnc == rnc).first()
        else:
            comp = self.db.query(Company).filter(Company.nombre == nombre).first()

        if not comp:
            comp = Company(rnc=rnc or None, nombre=nombre)
            self.db.add(comp)
            self.db.flush()
        return comp

    async def _get_or_create_institution(self, r: dict) -> Optional[Institution]:
        codigo = str(r.get("codigo_institucion") or r.get("institucion_id", "")).strip()
        nombre = r.get("nombre_institucion") or r.get("institucion", "")
        if not nombre:
            return None

        if codigo:
            inst = self.db.query(Institution).filter(Institution.codigo == codigo).first()
        else:
            inst = self.db.query(Institution).filter(Institution.nombre == nombre).first()

        if not inst:
            inst = Institution(codigo=codigo or None, nombre=nombre, siglas=r.get("siglas"))
            self.db.add(inst)
            self.db.flush()
        return inst

    def _update_company_stats(self, company: Company):
        from sqlalchemy import func
        result = self.db.query(
            func.count(Contract.id).label("cnt"),
            func.sum(Contract.monto_original).label("monto"),
            func.count(func.distinct(Contract.institution_id)).label("inst"),
        ).filter(Contract.company_id == company.id).first()
        if result:
            company.total_contratos = result.cnt or 0
            company.total_monto_recibido = result.monto or 0
            company.total_instituciones = result.inst or 0

    def _update_institution_stats(self, institution: Institution):
        from sqlalchemy import func
        result = self.db.query(
            func.count(Contract.id).label("cnt"),
            func.sum(Contract.monto_original).label("monto"),
        ).filter(Contract.institution_id == institution.id).first()
        if result:
            institution.total_contratos = result.cnt or 0
            institution.total_monto_contratos = result.monto or 0

    @staticmethod
    def _parse_monto(val) -> float:
        if not val:
            return 0.0
        try:
            return float(str(val).replace(",", "").replace("RD$", "").replace("$", "").strip())
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _parse_date(val) -> Optional[datetime]:
        if not val:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(str(val).split("T")[0], fmt)
            except ValueError:
                continue
        return None


async def run_dgcp_scraper(max_pages: int = 100):
    scraper = DGCPScraper()
    return await scraper.run(max_pages)
