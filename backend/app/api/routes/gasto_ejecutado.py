import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.institution import Institution

router = APIRouter(prefix="/gasto-ejecutado", tags=["Gasto Ejecutado"])

GASTO_DB = Path(__file__).parent.parent.parent.parent / "data" / "gasto_ejecutado.db"

CAVEAT = (
    "Fuente: Ministerio de Hacienda y Economía — Estadísticas de Ejecución de los "
    "Gastos y Aplicaciones Financieras (portal de transparencia / datos.gob.do). "
    "'Devengado' es el gasto que el propio gobierno reporta como realmente "
    "ejecutado, distinto de lo presupuestado/adjudicado. Los nombres de "
    "instituciones varían entre años (ej. 'Secretaría de Estado' vs 'Ministerio' "
    "tras la reforma de 2010) por lo que el cruce con la ficha de institución es "
    "best-effort y puede no encontrar coincidencia en años antiguos."
)


def _norm(s: str) -> str:
    n = (s or "").upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    return n.strip()


def get_conn():
    if not GASTO_DB.exists():
        raise HTTPException(status_code=503, detail="Base de datos de gasto ejecutado no disponible")
    conn = sqlite3.connect(str(GASTO_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _institution_lookup(db: Session) -> dict:
    rows = db.query(Institution.id, Institution.nombre, Institution.siglas).all()
    by_norm = {}
    for inst_id, nombre, siglas in rows:
        if nombre:
            by_norm.setdefault(_norm(nombre), inst_id)
        if siglas:
            by_norm.setdefault(_norm(siglas), inst_id)
    return by_norm


@router.get("/stats")
def stats():
    conn = get_conn()
    try:
        total_devengado = conn.execute("SELECT SUM(devengado) FROM gasto_institucion").fetchone()[0] or 0
        total_vigente = conn.execute("SELECT SUM(presupuesto_vigente) FROM gasto_institucion").fetchone()[0] or 0
        anios = [r[0] for r in conn.execute(
            "SELECT DISTINCT anio FROM gasto_institucion ORDER BY anio"
        ).fetchall()]
        num_inst = conn.execute("SELECT COUNT(DISTINCT institucion_norm) FROM gasto_institucion").fetchone()[0]
        return {
            "total_devengado": round(total_devengado, 0),
            "total_presupuesto_vigente": round(total_vigente, 0),
            "anios_disponibles": anios,
            "num_instituciones": num_inst,
            "caveat": CAVEAT,
        }
    finally:
        conn.close()


@router.get("/serie-historica")
def serie_historica():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT anio,
                   ROUND(SUM(devengado), 0) AS devengado,
                   ROUND(SUM(presupuesto_vigente), 0) AS presupuesto_vigente
            FROM gasto_institucion
            GROUP BY anio
            ORDER BY anio
        """).fetchall()
        return {"results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/por-institucion")
def por_institucion(
    anio: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    conn = get_conn()
    try:
        where = f"WHERE anio = {anio}" if anio else ""
        rows = conn.execute(f"""
            SELECT institucion, institucion_norm,
                   ROUND(SUM(presupuesto_inicial), 0) AS presupuesto_inicial,
                   ROUND(SUM(presupuesto_vigente), 0) AS presupuesto_vigente,
                   ROUND(SUM(devengado), 0)           AS devengado,
                   MIN(anio) AS primer_anio, MAX(anio) AS ultimo_anio
            FROM gasto_institucion
            {where}
            GROUP BY institucion_norm
            ORDER BY devengado DESC
        """).fetchall()
        results = [dict(r) for r in rows]
        lookup = _institution_lookup(db)
        for r in results:
            r["institution_id"] = lookup.get(r["institucion_norm"])
            r["pct_ejecucion"] = round(100 * r["devengado"] / r["presupuesto_vigente"], 1) if r["presupuesto_vigente"] else None
        total = len(results)
        offset = (page - 1) * size
        return {"total": total, "page": page, "size": size, "results": results[offset:offset + size], "caveat": CAVEAT}
    finally:
        conn.close()


@router.get("/detalle")
def detalle(
    institucion_norm: str = Query(..., description="Valor de 'institucion_norm' devuelto por /por-institucion"),
    anio: Optional[int] = None,
):
    """El 'motivo' (programa/actividad presupuestaria) y la 'fecha' (año/mes) del
    gasto devengado de una institución. Hacienda no publica detalle por proveedor o
    factura individual — este es el nivel más granular que el dataset oficial expone."""
    conn = get_conn()
    try:
        where = f"AND anio = {anio}" if anio else ""
        rows = conn.execute(f"""
            SELECT institucion FROM gasto_institucion WHERE institucion_norm = ? LIMIT 1
        """, (institucion_norm,)).fetchone()
        if not rows:
            raise HTTPException(status_code=404, detail="Institución no encontrada en gasto ejecutado")
        nombre = rows["institucion"]

        detalle_rows = conn.execute(f"""
            SELECT programa, actividad, anio, mes, ROUND(SUM(devengado), 0) AS devengado
            FROM gasto_detalle
            WHERE institucion_norm = ? {where}
            GROUP BY programa, actividad, anio, mes
            HAVING devengado > 0
            ORDER BY anio DESC, mes DESC, devengado DESC
            LIMIT 500
        """, (institucion_norm,)).fetchall()
        return {
            "institucion": nombre,
            "results": [dict(r) for r in detalle_rows],
            "caveat": (
                "Nivel más granular publicado por Hacienda: programa/actividad presupuestaria "
                "y mes. No incluye proveedor, factura ni descripción libre del gasto — eso solo "
                "existe para compras vía DGCP (ver pestaña Contratos)."
            ),
        }
    finally:
        conn.close()


@router.get("/por-funcion")
def por_funcion(anio: Optional[int] = None):
    conn = get_conn()
    try:
        where = f"WHERE anio = {anio}" if anio else ""
        rows = conn.execute(f"""
            SELECT finalidad,
                   ROUND(SUM(presupuesto_vigente), 0) AS presupuesto_vigente,
                   ROUND(SUM(devengado), 0)           AS devengado
            FROM gasto_funcion
            {where}
            GROUP BY finalidad
            ORDER BY devengado DESC
        """).fetchall()
        return {"results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/baja-ejecucion")
def baja_ejecucion(
    anio: Optional[int] = None,
    umbral: float = Query(0.5, ge=0, le=1, description="% máximo de ejecución (devengado/vigente) para considerarse baja ejecución"),
    db: Session = Depends(get_db),
):
    """Instituciones a las que se les aprobó presupuesto y gastaron muy poco de él.
    Nota: en este dataset 'Devengado' nunca supera 'Presupuesto Vigente' (el vigente
    ya incorpora las modificaciones presupuestarias del año), así que la sobre-
    ejecución no es una señal disponible aquí — la baja ejecución sí lo es."""
    conn = get_conn()
    try:
        where = f"AND anio = {anio}" if anio else ""
        rows = conn.execute(f"""
            SELECT institucion, institucion_norm, anio,
                   ROUND(SUM(presupuesto_vigente), 0) AS presupuesto_vigente,
                   ROUND(SUM(devengado), 0)           AS devengado
            FROM gasto_institucion
            WHERE presupuesto_vigente > 0 {where}
            GROUP BY institucion_norm, anio
            HAVING devengado <= presupuesto_vigente * ?
            ORDER BY (presupuesto_vigente - devengado) DESC
            LIMIT 100
        """, (umbral,)).fetchall()
        results = [dict(r) for r in rows]
        lookup = _institution_lookup(db)
        for r in results:
            r["institution_id"] = lookup.get(r["institucion_norm"])
            r["sin_ejecutar"] = r["presupuesto_vigente"] - r["devengado"]
            r["pct_ejecucion"] = round(100 * r["devengado"] / r["presupuesto_vigente"], 1) if r["presupuesto_vigente"] else None
        return {"results": results, "caveat": CAVEAT}
    finally:
        conn.close()
