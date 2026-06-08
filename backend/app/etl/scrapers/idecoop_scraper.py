"""
Scraper IDECOOP — Instituto de Desarrollo y Crédito Cooperativo.
Fuente principal: idecoop.gob.do (ETL en vivo, sin datos sembrados — ver nota abajo)
Fuente secundaria: DGCP (contratos donde proveedor = cooperativa por nombre/RNC)

El scraper hace dos cosas:
1. Intenta scraping del portal IDECOOP para datos oficiales de cooperativas incorporadas
2. Cruza nombres/RNCs de las cooperativas obtenidas con la tabla de contratos DGCP
   para detectar cooperativas con contratos del Estado

──────────────────────────────────────────────────────────────────────────────
CORRECCIÓN APLICADA EN ESTA SESIÓN (2026-06-07) — eliminación de catálogo sembrado
──────────────────────────────────────────────────────────────────────────────
La versión anterior de este archivo incluía un `COOPERATIVAS_SEED` con 66
"cooperativas" (el docstring decía "~200") cuyos datos eran, casi en su
totalidad, INVENTADOS:
  - 65 de las 66 entradas no tenían RNC (campo en None/null).
  - `num_socios` y `activos_totales` eran cifras redondas sin fuente
    (ej. 4_500, 12_000_000_000) — y de ahí se derivaban también
    `patrimonio` (×0.35) y `capital_social` (×0.20), multiplicando la
    fabricación.
  - `fuente` decía literalmente "IDECOOP / Seed GovTracker RD" — una
    auto-cita interna, no una fuente verificable.
  - Varios NOMBRES completos parecen inventados por completo, sin que
    exista ningún registro público de su existencia: "COOPEDIVINO —
    Cooperativa Productores de Cacao Divino", "COOPEGUAVAS — Cooperativa
    de Productores de Guayaba", "COOPERATIVA MAICERA DEL SUR", "COOPERATIVA
    MAGISTERIAL — Cooperativa de Maestros del Sur", "COOPINTELECTO",
    "COOPERATIVA ELÉCTRICA DE CONSTANZA" (no existe distribución eléctrica
    cooperativa en RD), "COOPPERIODISTAS", "COOPETECH", etc.

Se investigó exhaustivamente si existe ALGUNA fuente oficial (no
periodística, según la regla del usuario) con un listado verificable de
cooperativas + RNC + cifras financieras:
  - https://idecoop.gob.do/servicios/cooperativas-incorporadas/ — la propia
    IDECOOP describe el servicio ("se muestran las cooperativas incorporadas
    para conocimiento público") pero la página NO expone ninguna tabla,
    listado, ni archivo descargable: es solo texto descriptivo + datos de
    contacto. Confirmado leyendo el HTML crudo (sin JS) — no hay `<table>`,
    PDF, XLSX ni JSON embebido.
  - https://idecoop.gob.do/categoria/servicios/cooperativas-incorporadas —
    misma página genérica, sin entradas individuales de cooperativas.
  - https://idecoop.gob.do/transparencia/inicio — el portal de transparencia
    institucional NO incluye ningún apartado de registro/listado de
    cooperativas, estadísticas por entidad, ni boletines del sector
    (solo presupuesto, RRHH, compras, activos fijos — typical institutional
    transparency, nada específico de cooperativas).
  - https://www.conacoop.com.do/directorio/ (Consejo Nacional de
    Cooperativas) — el directorio existe como sección pero no publica datos
    (placeholder vacío en el HTML).
  - DGII (consulta RNC) — requiere búsqueda interactiva uno-por-uno vía
    formulario ASP.NET con tokens de sesión (__VIEWSTATE/postback AJAX);
    no existe un dataset público descargable para cruzar 66 nombres, y no
    se encontró ninguna mención oficial (gaceta, ley, resolución) que
    confirme el RNC de ninguna de las cooperativas del catálogo — ni
    siquiera de COOPEDUC, la única que tenía RNC en el seed anterior.

Conclusión: NO existe ningún documento oficial público, descargable o
consultable en bloque, que permita verificar nombres + RNC + cifras de
cooperativas dominicanas. Igual que se hizo con `FONDOS_ESTADO_SEED` y
`_cruzar_con_empresas()` en `sib_scraper.py` (eliminados por completo por
falta de fuente oficial citable), se ELIMINA aquí el catálogo sembrado
`COOPERATIVAS_SEED` y la función `_seed_cooperativas()` — "omitir en vez
de inventar" aplicado a su máxima expresión: ninguna cooperativa con datos
fabricados es mejor que 66 con datos fabricados.

El scraper queda como un ETL puramente en vivo (igual que `dgcp_scraper.py`,
ya marcado "✅ limpio — ETL en vivo sin datos sembrados"): si el portal de
IDECOOP llega a publicar un listado tabular real, `_scrape_portal()` lo
recogerá automáticamente y creará los registros con `fuente="IDECOOP Portal"
(datos en vivo)`, preservando la trazabilidad. Mientras tanto, la tabla
`cooperativas` permanece vacía — preferible a mostrar datos inventados.
"""
import asyncio
import re
import httpx
from datetime import datetime
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup
from ...core.config import settings
from ...core.database import SessionLocal
from ...models.cooperative import Cooperative, CoopType, CoopStatus
from ...models.contract import Contract
from sqlalchemy import func


class IdecoopScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper IDECOOP...")
        scraped = await self._scrape_portal()
        await self._cruzar_con_contratos()
        self.db.close()
        logger.info(f"IDECOOP: {scraped} del portal, cruce completado")
        return scraped

    async def _scrape_portal(self) -> int:
        """Intenta obtener datos actualizados del portal IDECOOP."""
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                          headers={"User-Agent": settings.USER_AGENT}) as client:
                # Intentar varias rutas comunes del portal
                for path in ["/cooperativas", "/registro", "/cooperativas/listado",
                              "/estadisticas", "/publicaciones"]:
                    try:
                        resp = await client.get(f"https://idecoop.gob.do{path}")
                        if resp.status_code == 200:
                            count = await self._parse_idecoop_page(resp.text)
                            if count > 0:
                                return count
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Portal IDECOOP no accesible: {e}")
        return 0

    async def _parse_idecoop_page(self, html: str) -> int:
        """Parsea HTML del portal IDECOOP para extraer datos de cooperativas."""
        soup = BeautifulSoup(html, "lxml")
        count = 0

        # Buscar tablas con datos de cooperativas
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 3:
                    nombre = cells[0] if cells else None
                    if nombre and len(nombre) > 5:
                        await self._upsert_from_portal(cells)
                        count += 1
        return count

    async def _upsert_from_portal(self, cells: list):
        """Crea o actualiza una cooperativa desde datos del portal."""
        nombre = cells[0].strip() if cells else None
        if not nombre:
            return
        existing = self.db.query(Cooperative).filter(
            Cooperative.nombre.ilike(f"%{nombre[:30]}%")
        ).first()
        if not existing:
            coop = Cooperative(nombre=nombre, fuente="IDECOOP Portal (datos en vivo, idecoop.gob.do)",
                               url_fuente="https://idecoop.gob.do/servicios/cooperativas-incorporadas/")
            # Intentar extraer más campos según posición
            if len(cells) > 1: coop.tipo = _detect_tipo(cells[1])
            if len(cells) > 2: coop.provincia = cells[2]
            if len(cells) > 3:
                try: coop.num_socios = int(re.sub(r'\D', '', cells[3]) or '0')
                except: pass
            self.db.add(coop)
            self.db.flush()

    async def _cruzar_con_contratos(self):
        """
        Cruza cooperativas por nombre/RNC con la tabla de contratos DGCP.
        Cualquier empresa cuyo nombre contenga "COOPERATIVA" o "COOPE" o "COOP"
        o cuyo RNC coincida se marca como vinculada.
        """
        coops = self.db.query(Cooperative).all()
        for coop in coops:
            # Buscar por RNC
            if coop.rnc:
                from ...models.company import Company
                comp = self.db.query(Company).filter(Company.rnc == coop.rnc).first()
                if comp:
                    coop.total_contratos_estado = comp.total_contratos
                    coop.total_monto_contratos  = comp.total_monto_recibido
                    continue

            # Buscar por coincidencia de nombre
            siglas = coop.siglas or ""
            nombre_corto = coop.nombre.split("—")[0].strip()[:40] if "—" in coop.nombre else coop.nombre[:40]

            from ...models.company import Company
            from sqlalchemy import or_
            comp = self.db.query(Company).filter(
                or_(
                    Company.nombre.ilike(f"%{nombre_corto}%"),
                    Company.nombre.ilike(f"%{siglas}%") if siglas else Company.nombre.is_(None),
                )
            ).first()
            if comp:
                coop.total_contratos_estado = comp.total_contratos
                coop.total_monto_contratos  = comp.total_monto_recibido

        self.db.commit()


def _detect_tipo(text: str) -> CoopType:
    t = text.lower()
    if any(k in t for k in ["ahorro", "crédito", "credito", "financiero"]):
        return CoopType.AHORRO_CREDITO
    if any(k in t for k in ["agro", "agrícola", "agropecuaria", "café", "cacao", "arroz"]):
        return CoopType.AGROPECUARIA
    if "transport" in t:
        return CoopType.TRANSPORTE
    if "vivienda" in t or "habitat" in t:
        return CoopType.VIVIENDA
    if "salud" in t or "médico" in t:
        return CoopType.SALUD
    if "consumo" in t:
        return CoopType.CONSUMO
    if "escolar" in t or "universit" in t:
        return CoopType.ESCOLAR
    if "producción" in t or "produccion" in t:
        return CoopType.PRODUCCION
    return CoopType.SERVICIOS_MULTIPLES


async def run_idecoop_scraper():
    scraper = IdecoopScraper()
    return await scraper.run()
