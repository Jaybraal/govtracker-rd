"""
Importador de Ejecución Presupuestaria del Estado — fuente oficial Ministerio de
Hacienda y Economía (MHE), portal de transparencia: hacienda.gob.do

Estos son los gastos que el propio gobierno reporta a Hacienda como "Devengado
Aprobado" — el gasto REALMENTE ejecutado, no solo lo adjudicado/presupuestado.
Cubre 2017-2025, 144 instituciones. Datasets publicados también en datos.gob.do
bajo la organización "Ministerio de Hacienda y Economía (MHE)".
"""
import csv
import re
import sqlite3
import unicodedata
from pathlib import Path

import httpx
from loguru import logger

GASTO_DB = Path(__file__).parent.parent.parent.parent / "data" / "gasto_ejecutado.db"

URL_POR_INSTITUCION = "https://www.hacienda.gob.do/transparencia/wp-content/uploads/2026/01/Estadisticas-de-ejecucion-de-los-gastos-por-institucion.csv"
URL_POR_FUNCION = "https://www.hacienda.gob.do/transparencia/wp-content/uploads/2026/01/Estadisticas-de-ejecucion-de-los-gastos-por-funcion.csv"


def _norm(s: str) -> str:
    n = (s or "").upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    return n.strip()


def _clean_header(h: str) -> str:
    """Los CSV de Hacienda traen artefactos de codificación (guion suave \\xad, BOM)
    en algunos encabezados (ej. 'Capí\\xadtulo') — se normalizan para ubicar la
    columna sin depender del byte exacto."""
    return re.sub(r"[­﻿]", "", h or "").strip()


def _col(row: dict, *names: str) -> str:
    cleaned = {_clean_header(k): v for k, v in row.items()}
    for name in names:
        if name in cleaned:
            return cleaned[name] or ""
    return ""


def _to_float(s: str) -> float:
    if not s:
        return 0.0
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _ensure_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS gasto_institucion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institucion TEXT NOT NULL,
            institucion_norm TEXT NOT NULL,
            anio INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            presupuesto_inicial REAL DEFAULT 0,
            presupuesto_vigente REAL DEFAULT 0,
            devengado REAL DEFAULT 0,
            UNIQUE(institucion_norm, anio, mes)
        );
        CREATE INDEX IF NOT EXISTS idx_gasto_inst_norm ON gasto_institucion(institucion_norm);
        CREATE INDEX IF NOT EXISTS idx_gasto_inst_anio ON gasto_institucion(anio);

        CREATE TABLE IF NOT EXISTS gasto_funcion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finalidad TEXT NOT NULL,
            anio INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            presupuesto_vigente REAL DEFAULT 0,
            devengado REAL DEFAULT 0,
            UNIQUE(finalidad, anio, mes)
        );
        CREATE INDEX IF NOT EXISTS idx_gasto_fun_anio ON gasto_funcion(anio);

        CREATE TABLE IF NOT EXISTS gasto_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institucion_norm TEXT NOT NULL,
            anio INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            programa TEXT,
            actividad TEXT,
            devengado REAL DEFAULT 0,
            UNIQUE(institucion_norm, anio, mes, programa, actividad)
        );
        CREATE INDEX IF NOT EXISTS idx_gasto_det_inst ON gasto_detalle(institucion_norm, anio);
    """)
    conn.commit()


def _download(url: str) -> str:
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content.decode("utf-8-sig")


def import_por_institucion(conn: sqlite3.Connection, csv_text: str) -> int:
    agg: dict[tuple[str, int, int], list[float]] = {}
    reader = csv.DictReader(csv_text.splitlines(), delimiter=";")
    for row in reader:
        institucion = _col(row, "Capítulo").strip()
        periodo = _col(row, "Cod.Mes.Hist.Imputación").strip()
        if not institucion or "/" not in periodo:
            continue
        anio_s, mes_s = periodo.split("/")
        try:
            anio, mes = int(anio_s), int(mes_s)
        except ValueError:
            continue
        key = (institucion, anio, mes)
        vals = agg.setdefault(key, [0.0, 0.0, 0.0])
        vals[0] += _to_float(_col(row, "Pres. Inicial"))
        vals[1] += _to_float(_col(row, "Pres. Vigente Aprobado"))
        vals[2] += _to_float(_col(row, "Devengado Aprobado"))

    nuevos = 0
    for (institucion, anio, mes), (pres_inicial, pres_vigente, devengado) in agg.items():
        norm = _norm(institucion)
        cur = conn.execute(
            "SELECT id FROM gasto_institucion WHERE institucion_norm=? AND anio=? AND mes=?",
            (norm, anio, mes),
        ).fetchone()
        if cur:
            continue
        conn.execute(
            "INSERT INTO gasto_institucion (institucion, institucion_norm, anio, mes, presupuesto_inicial, presupuesto_vigente, devengado) "
            "VALUES (?,?,?,?,?,?,?)",
            (institucion, norm, anio, mes, pres_inicial, pres_vigente, devengado),
        )
        nuevos += 1
    conn.commit()
    return nuevos


def import_detalle(conn: sqlite3.Connection, csv_text: str) -> int:
    """Detalle por programa/actividad — el 'motivo' del gasto — y mes — la 'fecha' —
    a nivel institución. Hacienda no publica un detalle por proveedor/factura
    individual; este es el nivel más granular que el dataset oficial expone."""
    agg: dict[tuple, float] = {}
    reader = csv.DictReader(csv_text.splitlines(), delimiter=";")
    for row in reader:
        institucion = _col(row, "Capítulo").strip()
        programa = _col(row, "Programa").strip()
        actividad = _col(row, "Actividad / Obra").strip()
        periodo = _col(row, "Cod.Mes.Hist.Imputación").strip()
        if not institucion or "/" not in periodo:
            continue
        anio_s, mes_s = periodo.split("/")
        try:
            anio, mes = int(anio_s), int(mes_s)
        except ValueError:
            continue
        key = (_norm(institucion), anio, mes, programa, actividad)
        agg[key] = agg.get(key, 0.0) + _to_float(_col(row, "Devengado Aprobado"))

    nuevos = 0
    for (inst_norm, anio, mes, programa, actividad), devengado in agg.items():
        cur = conn.execute(
            "SELECT id FROM gasto_detalle WHERE institucion_norm=? AND anio=? AND mes=? AND programa=? AND actividad=?",
            (inst_norm, anio, mes, programa, actividad),
        ).fetchone()
        if cur:
            continue
        conn.execute(
            "INSERT INTO gasto_detalle (institucion_norm, anio, mes, programa, actividad, devengado) VALUES (?,?,?,?,?,?)",
            (inst_norm, anio, mes, programa, actividad, devengado),
        )
        nuevos += 1
    conn.commit()
    return nuevos


def import_por_funcion(conn: sqlite3.Connection, csv_text: str) -> int:
    agg: dict[tuple[str, int, int], list[float]] = {}
    reader = csv.DictReader(csv_text.splitlines(), delimiter=";")
    for row in reader:
        finalidad = _col(row, "Ref Funcion Finalidad").strip()
        periodo = _col(row, "Cod.Mes.Hist.Imputación").strip()
        if not finalidad or finalidad == "N/A" or "/" not in periodo:
            continue
        anio_s, mes_s = periodo.split("/")
        try:
            anio, mes = int(anio_s), int(mes_s)
        except ValueError:
            continue
        key = (finalidad, anio, mes)
        vals = agg.setdefault(key, [0.0, 0.0])
        vals[0] += _to_float(_col(row, "Pres. Vigente Aprobado"))
        vals[1] += _to_float(_col(row, "Devengado Aprobado"))

    nuevos = 0
    for (finalidad, anio, mes), (pres_vigente, devengado) in agg.items():
        cur = conn.execute(
            "SELECT id FROM gasto_funcion WHERE finalidad=? AND anio=? AND mes=?",
            (finalidad, anio, mes),
        ).fetchone()
        if cur:
            continue
        conn.execute(
            "INSERT INTO gasto_funcion (finalidad, anio, mes, presupuesto_vigente, devengado) VALUES (?,?,?,?,?)",
            (finalidad, anio, mes, pres_vigente, devengado),
        )
        nuevos += 1
    conn.commit()
    return nuevos


def run_import(descargar: bool = True) -> dict:
    GASTO_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(GASTO_DB))
    _ensure_schema(conn)
    try:
        logger.info("Importando Ejecución Presupuestaria — Ministerio de Hacienda y Economía...")
        csv_inst = _download(URL_POR_INSTITUCION)
        n_inst = import_por_institucion(conn, csv_inst)
        logger.info(f"Gasto por institución: {n_inst} filas nuevas (institución-año-mes)")

        n_det = import_detalle(conn, csv_inst)
        logger.info(f"Gasto detalle (programa/actividad): {n_det} filas nuevas")

        csv_fun = _download(URL_POR_FUNCION)
        n_fun = import_por_funcion(conn, csv_fun)
        logger.info(f"Gasto por función: {n_fun} filas nuevas (finalidad-año-mes)")

        return {"por_institucion_nuevos": n_inst, "detalle_nuevos": n_det, "por_funcion_nuevos": n_fun}
    finally:
        conn.close()


if __name__ == "__main__":
    print(run_import())
