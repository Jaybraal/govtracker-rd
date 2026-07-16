"""
Importador de nómina pública — Ministerio de Administración Pública (MAP).

MAP centraliza la "Nómina Pública General del Estado" para ~125 instituciones
de gobierno central en un único CSV mensual:

    https://map.gob.do/datosabiertos/data/nomina_publica_general_estado/csv
        ?year=<AAAA>&month=<M>

Columnas reales del CSV (verificado 2026-06-24, abril 2026): Nombre_del_empleado,
Institución, Cargo, Estatus, Suelto_Bruto (sic — typo de origen, sin "d"),
Género, Mes, Año.

Este proyecto YA tenía una nómina de 90 instituciones (`data/nominas.db`,
~7M filas) construida desde el portal de transparencia propio de cada
institución — más granular y con más historia que el snapshot de MAP. MAP
NO cubre ayuntamientos ni Aduanas (DGA), así que no reemplaza nada — solo se
usa para llenar instituciones grandes que faltaban en las 90: Ministerio de
Obras Públicas (MOPC), Ministerio de Educación (MINERD) y Servicio Nacional
de Salud (SNS), confirmadas presentes en el CSV de MAP con esos nombres
exactos.

Inserta en la misma tabla `empleados` de `data/nominas.db` que usan
diputados_nominas_scraper.py / pgr_nominas_scraper.py, para que toda la
detección de doble cobro / top salarios / por institución ya existente en
`/nominas/*` los incluya automáticamente sin cambios en esos endpoints.
"""
import re
import sqlite3
import unicodedata
from io import StringIO
from pathlib import Path
from typing import Optional

import csv
import httpx
from loguru import logger

NOMINAS_DB = Path(__file__).parent.parent.parent.parent / "data" / "nominas.db"
BASE_URL = "https://map.gob.do/datosabiertos/data/nomina_publica_general_estado/csv"

# Instituciones grandes confirmadas en el CSV de MAP que NO están en las 90
# ya cubiertas por scrapers individuales — ver docstring arriba. Si en el
# futuro se agregan más instituciones objetivo, agregar aquí su nombre EXACTO
# tal como aparece en la columna "Institución" del CSV de MAP.
INSTITUCIONES_OBJETIVO = {
    "Ministerio de Obras Públicas y Comunicaciones",
    "Ministerio de Educación",
    "Servicio Nacional de Salud",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _norm(s: str) -> str:
    n = s.upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^A-Z\s]", "", n)
    return n.strip()


def _connect():
    conn = sqlite3.connect(str(NOMINAS_DB), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            institucion TEXT NOT NULL,
            nombre_raw  TEXT,
            nombre      TEXT NOT NULL,
            funcion     TEXT,
            salario     REAL,
            mes         TEXT,
            anio        INTEGER,
            fuente      TEXT
        )
    """)
    conn.commit()
    return conn


def _fuente_existe(conn: sqlite3.Connection, fuente: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM empleados WHERE fuente=? LIMIT 1", (fuente,)).fetchone())


def _insertar_filas(conn: sqlite3.Connection, filas: list[dict]):
    conn.executemany("""
        INSERT INTO empleados (institucion, nombre_raw, nombre, funcion, salario, mes, anio, fuente)
        VALUES (:institucion, :nombre_raw, :nombre, :funcion, :salario, :mes, :anio, :fuente)
    """, filas)
    conn.commit()


def _salario(row: dict) -> Optional[float]:
    raw = row.get("Suelto_Bruto") or row.get("Sueldo_Bruto")
    if not raw:
        return None
    try:
        return float(str(raw).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


async def _fetch_mes(client: httpx.AsyncClient, anio: int, mes: int) -> Optional[str]:
    resp = await client.get(BASE_URL, params={"year": anio, "month": mes}, headers=HEADERS, timeout=180)
    if resp.status_code != 200 or not resp.content:
        return None
    return resp.content.decode("utf-8-sig", errors="replace")


class MapNominasScraper:
    def __init__(self, instituciones_objetivo: set[str] = None):
        self.instituciones_objetivo = instituciones_objetivo or INSTITUCIONES_OBJETIVO
        self.db = _connect()
        self.meses_procesados = 0
        self.meses_omitidos = 0
        self.filas_insertadas = 0

    async def run(self, anio: int, meses: list[int]) -> dict:
        async with httpx.AsyncClient() as client:
            for mes in meses:
                fuente = f"{BASE_URL}?year={anio}&month={mes}"
                if any(
                    _fuente_existe(self.db, f"{fuente}::{inst}")
                    for inst in self.instituciones_objetivo
                ):
                    logger.info(f"MAP nóminas {anio}-{mes:02d}: ya importado, se omite")
                    self.meses_omitidos += 1
                    continue

                logger.info(f"MAP nóminas: descargando {anio}-{mes:02d}...")
                texto = await _fetch_mes(client, anio, mes)
                if not texto:
                    logger.warning(f"MAP nóminas {anio}-{mes:02d}: sin datos (mes no publicado aún?)")
                    self.meses_omitidos += 1
                    continue

                filas_mes = 0
                reader = csv.DictReader(StringIO(texto))
                batch = []
                for row in reader:
                    institucion = (row.get("Institución") or "").strip()
                    if institucion not in self.instituciones_objetivo:
                        continue
                    nombre_raw = (row.get("Nombre_del_empleado") or "").strip()
                    salario = _salario(row)
                    if not nombre_raw or salario is None:
                        continue
                    batch.append({
                        "institucion": institucion,
                        "nombre_raw": nombre_raw,
                        "nombre": _norm(nombre_raw),
                        "funcion": (row.get("Cargo") or "").strip() or None,
                        "salario": salario,
                        "mes": f"{mes:02d}",
                        "anio": anio,
                        "fuente": f"{fuente}::{institucion}",
                    })
                if batch:
                    _insertar_filas(self.db, batch)
                    filas_mes = len(batch)
                    self.filas_insertadas += filas_mes

                self.meses_procesados += 1
                logger.info(f"MAP nóminas {anio}-{mes:02d}: {filas_mes} filas de instituciones objetivo")

        self.db.close()
        return {
            "meses_procesados": self.meses_procesados,
            "meses_omitidos": self.meses_omitidos,
            "filas_insertadas": self.filas_insertadas,
        }


async def run_map_nominas_scraper(anio: int, meses: list[int] = None) -> dict:
    meses = meses or list(range(1, 13))
    scraper = MapNominasScraper()
    return await scraper.run(anio, meses)
