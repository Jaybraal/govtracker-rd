import sqlite3
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pathlib import Path

router = APIRouter(prefix="/pgr", tags=["PGR — Procuraduría"])

PGR_DB = Path(__file__).parent.parent.parent.parent / "data" / "pgr.db"


def get_conn():
    if not PGR_DB.exists():
        raise HTTPException(
            status_code=503,
            detail="Base de datos PGR no disponible. Ejecuta el scraper primero: POST /api/etl/scrape/pgr",
        )
    conn = sqlite3.connect(str(PGR_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/stats")
def pgr_stats():
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM comunicados").fetchone()[0]
        con_fecha = conn.execute(
            "SELECT COUNT(*) FROM comunicados WHERE fecha IS NOT NULL"
        ).fetchone()[0]
        por_tipo = {
            r["tipo"]: r["cnt"]
            for r in conn.execute(
                "SELECT tipo, COUNT(*) AS cnt FROM comunicados GROUP BY tipo ORDER BY cnt DESC"
            ).fetchall()
        }
        operaciones = [
            {"operacion": r["operacion"], "cantidad": r["cnt"]}
            for r in conn.execute("""
                SELECT operacion, COUNT(*) AS cnt
                FROM comunicados
                WHERE operacion IS NOT NULL
                GROUP BY operacion
                ORDER BY cnt DESC
            """).fetchall()
        ]
        recientes = conn.execute("""
            SELECT titulo, fecha, tipo, operacion, url
            FROM comunicados
            ORDER BY rowid DESC
            LIMIT 5
        """).fetchall()
        return {
            "total_comunicados": total,
            "con_fecha_extraida": con_fecha,
            "por_tipo": por_tipo,
            "operaciones_detectadas": operaciones,
            "recientes": [dict(r) for r in recientes],
        }
    finally:
        conn.close()


@router.get("/comunicados")
def listar_comunicados(
    tipo: Optional[str] = None,
    operacion: Optional[str] = None,
    q: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
):
    conn = get_conn()
    try:
        conditions = ["1=1"]
        if tipo:
            conditions.append(f"tipo = '{tipo.replace(chr(39), chr(39)*2)}'")
        if operacion:
            op_safe = operacion.replace("'", "''")
            conditions.append(f"operacion LIKE '%{op_safe}%'")
        if q and len(q) >= 3:
            q_safe = q.replace("'", "''")
            conditions.append(
                f"(titulo LIKE '%{q_safe}%' OR cuerpo LIKE '%{q_safe}%' OR imputados LIKE '%{q_safe}%')"
            )
        if desde:
            conditions.append(f"fecha >= '{desde}'")
        if hasta:
            conditions.append(f"fecha <= '{hasta}'")

        where = "WHERE " + " AND ".join(conditions)
        total = conn.execute(f"SELECT COUNT(*) FROM comunicados {where}").fetchone()[0]
        offset = (page - 1) * size
        rows = conn.execute(f"""
            SELECT id, url, titulo, fecha, tipo, operacion, montos, imputados,
                   SUBSTR(cuerpo, 1, 300) AS resumen
            FROM comunicados
            {where}
            ORDER BY rowid DESC
            LIMIT {size} OFFSET {offset}
        """).fetchall()
        return {"total": total, "page": page, "size": size, "results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/comunicados/{comunicado_id}")
def get_comunicado(comunicado_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM comunicados WHERE id = ?", (comunicado_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Comunicado no encontrado")
        return dict(row)
    finally:
        conn.close()


@router.get("/operaciones")
def listar_operaciones():
    """Lista todas las operaciones/casos detectados con sus comunicados."""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT
                operacion,
                COUNT(*)                     AS total_comunicados,
                MIN(fecha)                   AS primera_fecha,
                MAX(fecha)                   AS ultima_fecha,
                GROUP_CONCAT(DISTINCT tipo)  AS tipos,
                MAX(montos)                  AS montos_mencionados
            FROM comunicados
            WHERE operacion IS NOT NULL
            GROUP BY operacion
            ORDER BY total_comunicados DESC
        """).fetchall()
        return {"results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/buscar")
def buscar(
    q: str = Query(..., min_length=3),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=100),
):
    conn = get_conn()
    try:
        q_safe = q.replace("'", "''")
        condition = (
            f"titulo LIKE '%{q_safe}%' OR cuerpo LIKE '%{q_safe}%' "
            f"OR imputados LIKE '%{q_safe}%' OR operacion LIKE '%{q_safe}%'"
        )
        total = conn.execute(f"SELECT COUNT(*) FROM comunicados WHERE {condition}").fetchone()[0]
        offset = (page - 1) * size
        rows = conn.execute(f"""
            SELECT id, url, titulo, fecha, tipo, operacion, montos, imputados,
                   SUBSTR(cuerpo, 1, 400) AS resumen
            FROM comunicados
            WHERE {condition}
            ORDER BY rowid DESC
            LIMIT {size} OFFSET {offset}
        """).fetchall()
        return {"total": total, "page": page, "size": size, "results": [dict(r) for r in rows]}
    finally:
        conn.close()
