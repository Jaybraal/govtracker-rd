"""
Scraper para Ministerio de Hacienda RD.
Fuente: datos.hacienda.gob.do — presupuesto y ejecución.
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
from ...models.institution import Institution


PRESUPUESTO_INSTITUCIONES = {
    # Listado de instituciones RD con sus códigos en el sistema Hacienda
    "101": ("Presidencia de la República", "PR"),
    "201": ("Ministerio de Interior y Policía", "MIP"),
    "202": ("Ministerio de Relaciones Exteriores", "MIREX"),
    "203": ("Ministerio de las Fuerzas Armadas", "MFFAA"),
    "204": ("Ministerio de Hacienda", "MH"),
    "205": ("Ministerio de Educación", "MINERD"),
    "206": ("Ministerio de Salud Pública", "MSP"),
    "207": ("Ministerio de Obras Públicas y Comunicaciones", "MOPC"),
    "208": ("Ministerio de Agricultura", "MA"),
    "209": ("Ministerio de Industria, Comercio y MiPymes", "MICM"),
    "210": ("Ministerio de Trabajo", "MT"),
    "211": ("Ministerio de Turismo", "MITUR"),
    "212": ("Ministerio de Medio Ambiente", "MMARN"),
    "213": ("Ministerio de Energía y Minas", "MEM"),
    "301": ("Poder Judicial", "PJ"),
    "302": ("Congreso Nacional", "CN"),
    "401": ("INAPA", "INAPA"),
    "402": ("EGEHID", "EGEHID"),
    "403": ("INTRANT", "INTRANT"),
    "404": ("Corporación del Acueducto y Alcantarillado de Santiago", "CORAASAN"),
}


class HaciendaScraper:
    """Importa presupuesto e instituciones desde Hacienda."""

    def __init__(self):
        self.db = SessionLocal()

    async def run(self):
        logger.info("Iniciando scraper Hacienda...")
        imported = await self._seed_institutions()
        await self._fetch_budget_execution()
        self.db.close()
        logger.info(f"Hacienda scraper: {imported} instituciones procesadas")
        return imported

    async def _seed_institutions(self) -> int:
        count = 0
        for codigo, (nombre, siglas) in PRESUPUESTO_INSTITUCIONES.items():
            existing = self.db.query(Institution).filter(Institution.codigo == codigo).first()
            if not existing:
                inst = Institution(
                    codigo=codigo, nombre=nombre, siglas=siglas,
                )
                self.db.add(inst)
                count += 1
        self.db.commit()
        return count

    async def _fetch_budget_execution(self):
        """Intenta descargar datos de ejecución presupuestaria."""
        year = datetime.now().year
        url = f"https://datos.hacienda.gob.do/dataset/ejecucion-presupuestaria-{year}"
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    logger.info(f"Ejecución presupuestaria {year} descargada")
                    # Aquí se procesaría el HTML/JSON/Excel de la respuesta
        except Exception as e:
            logger.warning(f"No se pudo obtener ejecución presupuestaria: {e}")

    async def import_from_csv(self, filepath: str):
        """Importa contratos desde archivo CSV de Hacienda."""
        import csv
        count = 0
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    await self._process_row(row)
                    count += 1
                except Exception as e:
                    logger.warning(f"Error fila {count}: {e}")
        self.db.commit()
        logger.info(f"CSV Hacienda: {count} filas procesadas")
        return count

    async def _process_row(self, row: dict):
        # Normalizar campos comunes en los CSV de Hacienda
        pass


async def run_hacienda_scraper():
    scraper = HaciendaScraper()
    return await scraper.run()
