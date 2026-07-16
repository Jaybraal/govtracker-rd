"""
Scraper DGII — Dirección General de Impuestos Internos.
Portal público: dgii.gov.do — Consulta de RNC.
Extrae: razón social, representante legal, estado, actividad económica, domicilio.
Todo es público — el RNC y sus datos son información fiscal pública en RD.
"""
import httpx
import asyncio
import re
from typing import Optional
from loguru import logger
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from ...core.database import SessionLocal
from ...models.company import Company, LegalRepresentative
from ...models.political_party import PoliticalParty


DGII_CONSULTA_URL = "https://dgii.gov.do/app/WebApps/ConsultasWeb/consultas/rnc.aspx"
DGII_API_URL      = "https://api.digital.gob.do/v3/contribuyentes"   # API Digital.gob.do (pública)


class DGIIScraper:
    """
    Enriquece empresas y partidos con datos del registro fiscal (DGII).
    Fuente 1: API Digital.gob.do/v3/contribuyentes (oficial, sin auth)
    Fuente 2: Portal web DGII como fallback
    """

    def __init__(self):
        self.db = SessionLocal()
        self._client: Optional[httpx.AsyncClient] = None

    async def run(self, limit: int = 200) -> int:
        logger.info("Iniciando scraper DGII...")
        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "GovTrackerRD/1.0 (consulta pública RNC)"},
            follow_redirects=True,
        ) as client:
            self._client = client
            enriched = await self._enrich_companies(limit)
            enriched += await self._enrich_parties()
        self.db.close()
        logger.info(f"DGII: {enriched} entidades enriquecidas")
        return enriched

    async def _enrich_companies(self, limit: int) -> int:
        companies = self.db.query(Company).filter(
            Company.rnc.isnot(None),
            Company.rnc != "",
        ).limit(limit).all()

        count = 0
        for comp in companies:
            try:
                data = await self._query_rnc(comp.rnc)
                if data:
                    await self._update_company(comp, data)
                    count += 1
                await asyncio.sleep(0.3)   # cortesía al servidor
            except Exception as e:
                logger.debug(f"RNC {comp.rnc}: {e}")
        self.db.commit()
        return count

    async def _enrich_parties(self) -> int:
        parties = self.db.query(PoliticalParty).filter(
            PoliticalParty.rnc.isnot(None)
        ).all()
        count = 0
        for party in parties:
            try:
                data = await self._query_rnc(party.rnc)
                if data and data.get("nombre"):
                    party.nombre = data["nombre"]
                    count += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"Partido RNC {party.rnc}: {e}")
        self.db.commit()
        return count

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def _query_rnc(self, rnc: str) -> Optional[dict]:
        """
        Consulta la API pública del Gobierno Digital RD.
        Endpoint: https://api.digital.gob.do/v3/contribuyentes?rnc=<rnc>
        Esta API es oficial, gratuita y no requiere autenticación.
        """
        rnc_clean = re.sub(r'\D', '', rnc)
        if not rnc_clean:
            return None

        # Intentar API Digital.gob.do primero
        try:
            resp = await self._client.get(
                DGII_API_URL,
                params={"rnc": rnc_clean},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return self._parse_api_response(data[0])
                if isinstance(data, dict) and data.get("rnc"):
                    return self._parse_api_response(data)
        except Exception as e:
            logger.debug(f"API Digital.gob.do falló para {rnc}: {e}")

        # Fallback: portal web DGII
        return await self._scrape_dgii_portal(rnc_clean)

    def _parse_api_response(self, data: dict) -> dict:
        return {
            "rnc":               data.get("rnc", ""),
            "nombre":            data.get("nombre", "") or data.get("razon_social", ""),
            "nombre_comercial":  data.get("nombre_comercial", ""),
            "estado":            data.get("estado", ""),
            "actividad":         data.get("actividad_economica", "") or data.get("categoria", ""),
            "representante":     data.get("nombre_representante", "") or data.get("representante_legal", ""),
            "cedula_repr":       data.get("cedula_representante", ""),
            "tipo":              data.get("tipo_rnc", "") or data.get("tipo", ""),
            "regimen_pagos":     data.get("regimen_de_pagos", ""),
            "fecha_registro":    data.get("fecha_inicio_actividades", ""),
            "categoria_dgii":    data.get("categoria", ""),
        }

    async def _scrape_dgii_portal(self, rnc: str) -> Optional[dict]:
        """Scraping del portal DGII como fallback."""
        try:
            resp = await self._client.get(
                DGII_CONSULTA_URL,
                params={"RNC": rnc},
            )
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            result = {}
            # Buscar tabla de resultados típica del portal DGII
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    key   = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if "razón" in key or "nombre" in key:
                        result["nombre"] = value
                    elif "representante" in key:
                        result["representante"] = value
                    elif "actividad" in key:
                        result["actividad"] = value
                    elif "estado" in key:
                        result["estado"] = value
            return result if result else None
        except Exception as e:
            logger.debug(f"Portal DGII scraping falló para {rnc}: {e}")
            return None

    async def _update_company(self, comp: Company, data: dict):
        """Actualiza la empresa con datos de DGII."""
        if data.get("nombre") and not comp.nombre:
            comp.nombre = data["nombre"]
        if data.get("nombre_comercial"):
            comp.nombre_comercial = data["nombre_comercial"]
        if data.get("actividad") and not comp.sector:
            comp.sector = data["actividad"][:200]

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


# ─────────────────────────────────────────────────────────────────────────────
# Función directa para enriquecer una empresa específica por RNC o ID
# ─────────────────────────────────────────────────────────────────────────────
async def enrich_company_by_rnc(rnc: str) -> Optional[dict]:
    scraper = DGIIScraper()
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        scraper._client = client
        result = await scraper._query_rnc(rnc)
    scraper.db.close()
    return result


async def run_dgii_scraper(limit: int = 200) -> int:
    scraper = DGIIScraper()
    return await scraper.run(limit)
