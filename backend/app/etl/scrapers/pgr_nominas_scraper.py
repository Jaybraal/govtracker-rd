"""
Importador de nóminas de empleados — Procuraduría General de la República
(transparencia.pgr.gob.do).

La PGR no estaba en el dataset original de nóminas (88 instituciones, datos
de Hacienda/portales individuales). Su nómina vive en un subdominio aparte
(transparencia.pgr.gob.do) bajo el plugin "WP File Download", organizada en:

    Recursos Humanos > Nóminas de Empleados (cat 319)
        └── <Año> (p.ej. 2026, 2025, ... 2015)
              └── <Mes> (Enero..Diciembre)
                    ├── Nómina Personal Fijo <Mes> <Año>.xlsx
                    ├── Nómina Personal Contratado <Mes> <Año>.xlsx
                    └── Nómina Personal Militar <Mes> <Año>.xlsx

Cada XLSX tiene una fila de cabecera variable (la posición cambia entre
"Fijo"/"Contratado"/"Militar"), así que detectamos la fila de cabecera
buscando la celda "Cargo" y mapeamos columnas por nombre.

Inserta en data/nominas.db (tabla `empleados`), institucion =
"Procuraduría General de la República (PGR)". Es incremental: si la URL
del archivo (`fuente`) ya fue importada, se salta.
"""

import asyncio
import re
import sqlite3
import unicodedata
from io import BytesIO
from pathlib import Path
from random import uniform
from typing import Optional

import httpx
import openpyxl
from loguru import logger

NOMINAS_DB = Path(__file__).parent.parent.parent.parent / "data" / "nominas.db"
INSTITUCION = "Procuraduría General de la República (PGR)"

AJAX_URL = "https://transparencia.pgr.gob.do/wp-admin/admin-ajax.php"
ROOT_CAT_ID = 319  # "Nóminas de Empleados"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}

# Nombres de columnas que pueden contener cada dato (case-insensitive)
COL_NOMBRE = {"nombres y apellidos", "empleado", "nombre"}
COL_CARGO = {"cargo"}
COL_SALARIO = {"ingreso bruto", "salario"}


def _norm(s: str) -> str:
    n = s.upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^A-Z\s]", "", n)
    return n.strip()


def _norm_header(s) -> str:
    if s is None:
        return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip().lower()


def _mes_from_nombre(nombre: str) -> Optional[str]:
    nombre_low = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    for mes_nombre, mes_num in MESES.items():
        if mes_nombre in nombre_low:
            return mes_num
    return None


# ─── Base de datos ────────────────────────────────────────────────────────────
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


# ─── WP File Download API ─────────────────────────────────────────────────────
async def _get_categories(client: httpx.AsyncClient, cat_id: int) -> dict:
    params = {
        "juwpfisadmin": "false", "action": "wpfd",
        "task": "categories.display", "view": "categories",
        "id": cat_id, "top": ROOT_CAT_ID,
    }
    r = await client.get(AJAX_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


async def _get_files(client: httpx.AsyncClient, cat_id: int) -> list[dict]:
    params = {
        "juwpfisadmin": "false", "action": "wpfd",
        "task": "files.display", "view": "files",
        "id": cat_id, "rootcat": ROOT_CAT_ID, "page": 1,
        "orderCol": "ordering", "orderDir": "asc",
        "page_limit": 50, "show_files": 1,
    }
    r = await client.post(AJAX_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("files") or []


# ─── Parseo de XLSX ────────────────────────────────────────────────────────────
def _parse_xlsx(content: bytes) -> list[dict]:
    """Devuelve lista de {nombre_raw, funcion, salario} desde un XLSX de nómina."""
    wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(values_only=True))
    header_idx = None
    cols: dict[str, int] = {}

    for i, row in enumerate(rows):
        headers = {_norm_header(c): j for j, c in enumerate(row)}
        if "cargo" in headers and any(h in headers for h in COL_NOMBRE):
            header_idx = i
            for h, j in headers.items():
                if h in COL_NOMBRE:
                    cols["nombre"] = j
                elif h in COL_CARGO:
                    cols["cargo"] = j
                elif h in COL_SALARIO:
                    cols["salario"] = j
            break

    if header_idx is None or "nombre" not in cols or "salario" not in cols:
        return []

    out = []
    for row in rows[header_idx + 1:]:
        if cols["nombre"] >= len(row) or cols["salario"] >= len(row):
            continue
        nombre_raw = row[cols["nombre"]]
        salario = row[cols["salario"]]
        if not isinstance(nombre_raw, str) or " " not in nombre_raw.strip():
            continue
        if not isinstance(salario, (int, float)):
            continue
        cargo = row[cols["cargo"]] if cols.get("cargo") is not None and cols["cargo"] < len(row) else None
        out.append({
            "nombre_raw": nombre_raw.strip(),
            "funcion": str(cargo).strip() if cargo else None,
            "salario": float(salario),
        })
    return out


# ─── Scraper principal ─────────────────────────────────────────────────────────
class PGRNominasScraper:
    def __init__(self, anio_desde: int = 2015, anio_hasta: int = 2026):
        self.anio_desde = anio_desde
        self.anio_hasta = anio_hasta
        self.db = _connect()
        self.archivos_procesados = 0
        self.archivos_omitidos = 0
        self.filas_insertadas = 0

    async def run(self) -> dict:
        async with httpx.AsyncClient() as client:
            root = await _get_categories(client, ROOT_CAT_ID)
            anios = [c for c in root.get("categories", []) if c["name"].isdigit()]
            anios = [c for c in anios if self.anio_desde <= int(c["name"]) <= self.anio_hasta]
            anios.sort(key=lambda c: int(c["name"]))

            for anio_cat in anios:
                anio = int(anio_cat["name"])
                logger.info(f"PGR Nóminas — año {anio}")
                meses_data = await _get_categories(client, anio_cat["term_id"])
                meses = meses_data.get("categories", [])

                for mes_cat in meses:
                    mes_num = _mes_from_nombre(mes_cat["name"])
                    if not mes_num:
                        continue

                    await asyncio.sleep(uniform(0.3, 0.8))
                    files = await _get_files(client, mes_cat["term_id"])
                    xlsx_files = [f for f in files if f.get("ext") == "xlsx"]

                    for f in xlsx_files:
                        url = f.get("linkdownload")
                        if not url:
                            continue
                        if _fuente_existe(self.db, url):
                            self.archivos_omitidos += 1
                            continue

                        await asyncio.sleep(uniform(0.3, 0.8))
                        try:
                            r = await client.get(url, headers=HEADERS, timeout=60)
                            r.raise_for_status()
                            registros = _parse_xlsx(r.content)
                        except Exception as e:
                            logger.warning(f"Error procesando {url}: {e}")
                            continue

                        filas = [{
                            "institucion": INSTITUCION,
                            "nombre_raw": reg["nombre_raw"],
                            "nombre": _norm(reg["nombre_raw"]),
                            "funcion": reg["funcion"],
                            "salario": reg["salario"],
                            "mes": mes_num,
                            "anio": anio,
                            "fuente": url,
                        } for reg in registros]

                        if filas:
                            _insertar_filas(self.db, filas)
                            self.filas_insertadas += len(filas)

                        self.archivos_procesados += 1
                        logger.debug(f"  ✓ {f.get('post_title')} — {len(filas)} registros")

        self.db.close()
        logger.info(
            f"PGR Nóminas finalizado — archivos: {self.archivos_procesados}, "
            f"omitidos: {self.archivos_omitidos}, filas insertadas: {self.filas_insertadas}"
        )
        return {
            "archivos_procesados": self.archivos_procesados,
            "archivos_omitidos": self.archivos_omitidos,
            "filas_insertadas": self.filas_insertadas,
        }


async def run_pgr_nominas_scraper(anio_desde: int = 2015, anio_hasta: int = 2026) -> dict:
    scraper = PGRNominasScraper(anio_desde=anio_desde, anio_hasta=anio_hasta)
    return await scraper.run()
