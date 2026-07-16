import re
import sqlite3
import os
import unicodedata
from functools import lru_cache
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pathlib import Path

router = APIRouter(prefix="/nominas", tags=["Nóminas"])

NOMINAS_DB = Path(__file__).parent.parent.parent.parent / "data" / "nominas.db"

def get_conn():
    if not NOMINAS_DB.exists():
        raise HTTPException(status_code=503, detail="Base de datos de nóminas no disponible")
    conn = sqlite3.connect(str(NOMINAS_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _norm(s: str) -> str:
    n = (s or "").upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^A-Z\s]", "", n)
    return n.strip()


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


@lru_cache(maxsize=8)
def _compute_conflicto_matches(instituciones: tuple) -> tuple:
    """
    Hace el cruce completo (nómina ~360K filas × representantes legales
    ~123K filas) y lo cachea en memoria del proceso — toma ~55s la primera
    vez por institución-set; sin esto, cada cambio de página/filtro en la UI
    repetiría el cálculo completo. El caché se invalida solo al reiniciar el
    proceso (los datos de origen no cambian salvo que se re-importen).
    """
    from ...core.database import SessionLocal
    from ...models.company import LegalRepresentative, Company

    db = SessionLocal()
    try:
        reps_por_nombre: dict[str, list] = {}
        rows = db.query(
            LegalRepresentative.nombre, LegalRepresentative.cedula, LegalRepresentative.cargo,
            Company.id, Company.nombre, Company.rnc, Company.total_contratos, Company.total_monto_recibido,
        ).join(Company, Company.id == LegalRepresentative.company_id).all()
        for nombre, cedula, cargo, company_id, company_nombre, rnc, total_contratos, total_monto in rows:
            key = _norm(nombre)
            if len(key) <= 6:  # evita falsos positivos triviales en nombres muy cortos/incompletos
                continue
            reps_por_nombre.setdefault(key, []).append({
                "cedula": cedula, "cargo": cargo, "company_id": company_id,
                "empresa": company_nombre, "rnc": rnc,
                "total_contratos": total_contratos, "total_monto_recibido": total_monto,
            })
    finally:
        db.close()

    conn = get_conn()
    try:
        placeholders = ",".join("?" for _ in instituciones)
        sql = f"""
            SELECT DISTINCT nombre, nombre_raw, institucion, funcion
            FROM empleados
            WHERE institucion IN ({placeholders})
              AND LENGTH(nombre) > 6
              AND funcion NOT LIKE '%MONTO_ANOMALO%'
        """
        empleados_rows = conn.execute(sql, instituciones).fetchall()
    finally:
        conn.close()

    matches = []
    vistos = set()
    for row in empleados_rows:
        nombre = row["nombre"]
        if nombre in vistos or nombre not in reps_por_nombre:
            continue
        vistos.add(nombre)
        num_tokens = len(nombre.split())
        num_empresas = len(reps_por_nombre[nombre])
        # Señal mucho más fuerte que "aparece como contacto de la empresa de
        # otro": la empresa contratista está registrada EXACTAMENTE a nombre
        # propio del empleado (persona física / EIRL bajo su propia
        # identidad) — coincidencia de nombre completo contra el nombre legal
        # de toda una empresa es estadísticamente mucho más rara que contra
        # un campo de "contacto registrado", así que se marca aparte.
        empresa_propia = any(_norm(r["empresa"]) == nombre for r in reps_por_nombre[nombre])
        # Nombres de pocos tokens (apellidos comunes dominicanos) y/o que
        # "representan" muchas empresas a la vez son casi siempre colisión de
        # nombre, no la misma persona — mismo criterio que ya usa el proyecto
        # en intelligence.py para descartar "gestores de constitución" cuando
        # num_repr es alto sin cédula. Sin cédula en ninguno de los dos lados
        # acá, así que la única señal estadística disponible es tokens + cantidad.
        if empresa_propia or (num_tokens >= 4 and num_empresas <= 2):
            nivel_confianza = "ALTA"
        elif num_tokens >= 3 and num_empresas <= 5:
            nivel_confianza = "MEDIA"
        else:
            nivel_confianza = "BAJA"
        matches.append({
            "nombre": row["nombre_raw"],
            "institucion_empleo": row["institucion"],
            "cargo_empleo": row["funcion"],
            "confianza": nivel_confianza,
            "empresa_propia": empresa_propia,
            "num_empresas": num_empresas,
            "representaciones": reps_por_nombre[nombre],
        })

    orden_confianza = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    matches.sort(key=lambda m: (
        orden_confianza[m["confianza"]],
        -sum(r["total_monto_recibido"] or 0 for r in m["representaciones"]),
    ))
    return tuple(matches)


@router.get("/conflicto-representantes")
def conflicto_representantes(
    instituciones: Optional[List[str]] = Query(
        None,
        description="Instituciones a cruzar; por defecto las 3 agregadas vía MAP (MOPC/MINERD/SNS)",
    ),
    confianza: Optional[str] = Query(None, description="Filtrar por ALTA/MEDIA/BAJA"),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
):
    """
    Cruza nómina de empleados públicos contra representantes/contactos
    registrados de empresas contratistas del Estado (RPE de DGCP): ¿algún
    empleado de la institución aparece también como representante legal de
    una empresa que le vende al Estado?

    Mismo patrón que la alerta POSIBLE_CONFLICTO para legisladores
    (services/alert_scanner.py), pero contra nómina en vez de la lista de
    diputados/senadores. Coincidencia por NOMBRE NORMALIZADO únicamente —
    ni la nómina de MAP ni el RPE de DGCP traen cédula, así que esto NUNCA
    confirma identidad por sí solo; es un punto de partida para
    verificación manual, no una acusación.
    """
    instituciones = instituciones or [
        "Ministerio de Obras Públicas y Comunicaciones",
        "Ministerio de Educación",
        "Servicio Nacional de Salud",
    ]
    matches = list(_compute_conflicto_matches(tuple(sorted(instituciones))))

    por_confianza = {
        nivel: sum(1 for m in matches if m["confianza"] == nivel)
        for nivel in ("ALTA", "MEDIA", "BAJA")
    }

    if confianza:
        matches = [m for m in matches if m["confianza"] == confianza.upper()]

    total = len(matches)
    offset = (page - 1) * size
    return {
        "total": total,
        "por_confianza": por_confianza,
        "page": page,
        "size": size,
        "instituciones_consultadas": instituciones,
        "caveat": (
            "Coincidencia por nombre normalizado únicamente, sin cédula de por medio en "
            "ninguna de las dos fuentes — NUNCA confirma identidad. 'confianza' es solo un "
            "proxy estadístico (más tokens en el nombre + menos empresas asociadas = menos "
            "probable que sea colisión de nombre común); incluso ALTA requiere verificación "
            "manual antes de concluir conflicto de interés"
        ),
        "results": matches[offset:offset + size],
    }
