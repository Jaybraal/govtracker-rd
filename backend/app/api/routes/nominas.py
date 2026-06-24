import sqlite3
import os
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pathlib import Path

router = APIRouter(prefix="/nominas", tags=["Nóminas"])

NOMINAS_DB = Path(__file__).parent.parent.parent.parent / "data" / "nominas.db"

def get_conn():
    if not NOMINAS_DB.exists():
        raise HTTPException(status_code=503, detail="Base de datos de nóminas no disponible")
    conn = sqlite3.connect(str(NOMINAS_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/stats")
def nominas_stats():
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM empleados").fetchone()[0]
        instituciones = conn.execute("SELECT COUNT(DISTINCT institucion) FROM empleados").fetchone()[0]
        anios = conn.execute(
            "SELECT anio FROM empleados WHERE anio BETWEEN 2010 AND 2026 GROUP BY anio ORDER BY anio DESC"
        ).fetchall()
        return {
            "total_registros": total,
            "total_instituciones": instituciones,
            "anios_disponibles": [r[0] for r in anios],
        }
    finally:
        conn.close()


@router.get("/doble-cobro")
def doble_cobro(
    anio: Optional[int] = None,
    confianza: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
):
    conn = get_conn()
    try:
        where = f"WHERE anio = {anio}" if anio else "WHERE anio BETWEEN 2010 AND 2026"
        q = f"""
            SELECT
                nombre,
                MIN(nombre_raw)                     AS nombre_original,
                CASE
                    WHEN LENGTH(nombre) > 22 THEN 'ALTA'
                    WHEN LENGTH(nombre) > 14 THEN 'MEDIA'
                    ELSE 'BAJA'
                END                                 AS confianza,
                COUNT(*)                            AS meses_afectados,
                MIN(anio || '/' || mes)             AS primer_periodo,
                MAX(anio || '/' || mes)             AS ultimo_periodo,
                MAX(num_inst)                       AS max_instituciones,
                GROUP_CONCAT(DISTINCT instituciones_mes) AS instituciones,
                ROUND(SUM(total_mes), 0)            AS total_cobrado
            FROM (
                SELECT
                    nombre,
                    MIN(nombre_raw)                   AS nombre_raw,
                    anio, mes,
                    COUNT(DISTINCT institucion)        AS num_inst,
                    GROUP_CONCAT(DISTINCT institucion) AS instituciones_mes,
                    SUM(CASE WHEN funcion NOT LIKE '%MONTO_ANOMALO%'
                             THEN salario ELSE 0 END)  AS total_mes
                FROM empleados
                {where}
                GROUP BY nombre, anio, mes
                HAVING num_inst > 1
                   AND nombre != ''
                   AND LENGTH(nombre) > 6
                   AND anio BETWEEN 2010 AND 2026
            ) sub
            GROUP BY nombre
            HAVING max_instituciones > 1
        """
        all_rows = conn.execute(q).fetchall()

        # Filtrar por confianza si se pide
        if confianza:
            confianza_upper = confianza.upper()
            all_rows = [r for r in all_rows if (
                ("ALTA" if len(r["nombre"]) > 22 else "MEDIA" if len(r["nombre"]) > 14 else "BAJA")
                == confianza_upper
            )]

        # Ordenar: ALTA primero, luego por max_instituciones, luego por total
        def sort_key(r):
            c = "ALTA" if len(r["nombre"]) > 22 else "MEDIA" if len(r["nombre"]) > 14 else "BAJA"
            return (0 if c == "ALTA" else 1 if c == "MEDIA" else 2, -r["max_instituciones"], -(r["total_cobrado"] or 0))

        all_rows = sorted(all_rows, key=sort_key)
        total = len(all_rows)
        offset = (page - 1) * size
        rows = all_rows[offset:offset + size]
        return {
            "total": total,
            "page": page,
            "size": size,
            "results": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/doble-cobro/detalle")
def doble_cobro_detalle(nombre: str = Query(..., min_length=3)):
    """Desglose mes a mes / institución por institución para una persona detectada en doble cobro."""
    conn = get_conn()
    try:
        nombre_norm = nombre.upper().strip()
        rows = conn.execute("""
            SELECT anio, mes, institucion, funcion, salario, nombre_raw
            FROM empleados
            WHERE nombre = ?
              AND anio BETWEEN 2010 AND 2026
              AND funcion NOT LIKE '%MONTO_ANOMALO%'
            ORDER BY anio, mes, institucion
        """, (nombre_norm,)).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Sin registros para esta persona")
        return {
            "nombre": nombre_norm,
            "nombre_original": rows[0]["nombre_raw"],
            "registros": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/top-salarios")
def top_salarios(
    anio: Optional[int] = None,
    institucion: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
):
    conn = get_conn()
    try:
        conditions = [
            "funcion NOT LIKE '%MONTO_ANOMALO%'",
            "anio BETWEEN 2010 AND 2026",
        ]
        if anio:
            conditions.append(f"anio = {anio}")
        if institucion:
            inst_safe = institucion.replace("'", "''")
            conditions.append(f"institucion LIKE '%{inst_safe}%'")

        where = "WHERE " + " AND ".join(conditions)
        q = f"""
            SELECT
                nombre_raw AS nombre,
                institucion,
                MAX(salario) AS salario_max,
                MIN(funcion) AS funcion,
                anio, mes
            FROM empleados
            {where}
            GROUP BY nombre, institucion
            ORDER BY salario_max DESC
            LIMIT 500
        """
        all_rows = conn.execute(q).fetchall()
        total = len(all_rows)
        offset = (page - 1) * size
        rows = all_rows[offset:offset + size]
        return {
            "total": total,
            "page": page,
            "size": size,
            "results": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/instituciones")
def por_institucion(anio: Optional[int] = None):
    conn = get_conn()
    try:
        conditions = [
            "funcion NOT LIKE '%MONTO_ANOMALO%'",
            "anio BETWEEN 2010 AND 2026",
        ]
        if anio:
            conditions.append(f"anio = {anio}")
        where = "WHERE " + " AND ".join(conditions)
        q = f"""
            SELECT
                institucion,
                COUNT(DISTINCT nombre)  AS empleados_unicos,
                ROUND(AVG(salario), 0)  AS salario_promedio,
                MAX(salario)            AS salario_max,
                ROUND(SUM(salario), 0)  AS masa_salarial_total,
                MAX(anio)               AS ultimo_anio
            FROM empleados
            {where}
            GROUP BY institucion
            ORDER BY masa_salarial_total DESC
            LIMIT 50
        """
        rows = conn.execute(q).fetchall()
        return {"results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/buscar")
def buscar_empleado(
    q: str = Query(..., min_length=3),
    anio: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
):
    import unicodedata, re

    def norm(s):
        n = s.upper().strip()
        n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
        n = re.sub(r"\s+", " ", n)
        n = re.sub(r"[^A-Z\s]", "", n)
        return n.strip()

    q_norm = norm(q)
    if len(q_norm) < 3:
        raise HTTPException(status_code=400, detail="Búsqueda muy corta")

    conn = get_conn()
    try:
        year_filter = f"AND anio = {anio}" if anio else "AND anio BETWEEN 2010 AND 2026"
        sql = f"""
            SELECT
                nombre_raw,
                nombre,
                institucion,
                funcion,
                salario,
                mes,
                anio
            FROM empleados
            WHERE nombre LIKE ?
              {year_filter}
              AND funcion NOT LIKE '%MONTO_ANOMALO%'
            ORDER BY anio DESC, salario DESC
            LIMIT 500
        """
        all_rows = conn.execute(sql, (f"%{q_norm}%",)).fetchall()
        total = len(all_rows)
        offset = (page - 1) * size
        rows = all_rows[offset:offset + size]
        return {
            "total": total,
            "page": page,
            "size": size,
            "results": [dict(r) for r in rows],
        }
    finally:
        conn.close()
