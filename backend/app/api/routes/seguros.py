import sqlite3
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pathlib import Path

router = APIRouter(prefix="/seguros", tags=["Seguros"])

SEGUROS_DB = Path(__file__).parent.parent.parent.parent / "data" / "seguros.db"

# Datos curados del caso SENASA — Operación Cobra (fuentes oficiales PGR)
CASO_SENASA = {
    "titulo": "Operación Cobra — SENASA",
    "descripcion": (
        "El 7 de diciembre de 2025 el Ministerio Público lanzó la 'Operación Cobra', "
        "desarticulando un entramado de corrupción dentro del Seguro Nacional de Salud (SeNaSa) "
        "encabezado por su exdirector ejecutivo Santiago Hazim (Hazim Albainy). "
        "Según la Procuraduría General de la República, el grupo defraudó al SeNaSa y a sus "
        "más de 7 millones de afiliados con al menos 15 mil millones de pesos y cobró "
        "sobornos superiores a 2 mil millones de pesos."
    ),
    "fecha": "2025-12-07",
    "fiscal": "Yeni Berenice Reynoso (Procuradora General de la República)",
    "imputados": [
        {"nombre": "Santiago Hazim (Hazim Albainy)", "cargo": "Exdirector ejecutivo de SENASA"},
        {"nombre": "Eduardo Read Estrella", "cargo": "Imputado — Operación Cobra"},
        {"nombre": "Francisco Iván Minaya Pérez", "cargo": "Imputado — Operación Cobra"},
        {"nombre": "Cinty Acosta Sención", "cargo": "Imputado — Operación Cobra"},
        {"nombre": "Heidi Mariela Pineda Perdomo", "cargo": "Imputado — Operación Cobra"},
        {"nombre": "Ramón Alan Speakler Mateo", "cargo": "Imputado — Operación Cobra"},
        {"nombre": "Rafael Luis Martínez Hazim", "cargo": "Imputado — Operación Cobra"},
        {"nombre": "Ada Ledesma Ubiera", "cargo": "Imputado — Operación Cobra"},
    ],
    "cargos_imputados": [
        "Coalición de funcionarios",
        "Prevaricación",
        "Asociación de malhechores",
        "Cobro de soborno",
        "Estafa contra el Estado dominicano",
        "Desfalco",
        "Falsificación",
        "Uso de documentos falsos",
        "Lavado de activos",
    ],
    "monto_defraudado": "Al menos RD$15,000,000,000",
    "monto_sobornos": "Más de RD$2,000,000,000",
    "afiliados_afectados": "Más de 7,000,000",
    "fuentes": [
        "https://pgr.gob.do/el-ministerio-publico-pone-en-marcha-la-operacion-cobra-inicia-judicializacion-en-busca-de-sanciones-penales-y-el-decomiso-del-dinero-sustraido-al-patrimonio-publico/",
        "https://pgr.gob.do/tribunal-ratifica-prision-preventiva-a-santiago-hazim-y-otros-6-procesados-a-partir-de-la-operacion-cobra/",
        "https://pgr.gob.do/ministerio-publico-asegura-que-hazim-albainy-encabezo-un-entramado-corrupto-para-beneficiarse-del-senasa/",
        "https://pgr.gob.do/entramado-de-corrupcion-impactado-con-la-operacion-cobra-capto-miles-de-millones-en-sobornos-para-enriquecerse/",
        "https://pgr.gob.do/3-imputados-de-la-operacion-cobra-confesaron-en-el-tribunal-que-pagaron-sobornos-a-funcionarios-del-senasa/",
    ],
}

INSTITUCIONES_SECTOR = [
    {"siglas": "SENASA",     "nombre": "Seguro Nacional de Salud",                                    "rol": "Seguro público de salud — más de 7M afiliados"},
    {"siglas": "SISALRIL",   "nombre": "Superintendencia de Salud y Riesgos Laborales",               "rol": "Regulador de ARS y ARL del sistema de seguridad social"},
    {"siglas": "CNSS",       "nombre": "Consejo Nacional de Seguridad Social",                        "rol": "Órgano rector del sistema de seguridad social"},
    {"siglas": "TSS",        "nombre": "Tesorería de la Seguridad Social",                            "rol": "Recauda y distribuye cotizaciones de seguridad social"},
    {"siglas": "PROMESECAL", "nombre": "Programa de Medicamentos Esenciales / CAL",                   "rol": "Adquisición y distribución de medicamentos esenciales"},
]


def get_conn():
    if not SEGUROS_DB.exists():
        raise HTTPException(status_code=503, detail="Base de datos de seguros no disponible")
    conn = sqlite3.connect(str(SEGUROS_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/stats")
def seguros_stats():
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM contratos_seguros").fetchone()[0]
        monto = conn.execute("SELECT SUM(valor_contratado) FROM contratos_seguros").fetchone()[0] or 0
        empresas = conn.execute("SELECT COUNT(DISTINCT empresa) FROM contratos_seguros").fetchone()[0]
        anios = [r[0] for r in conn.execute(
            "SELECT anio FROM contratos_seguros WHERE anio IS NOT NULL GROUP BY anio ORDER BY anio DESC"
        ).fetchall()]
        return {
            "total_contratos": total,
            "monto_total": round(monto, 0),
            "empresas_unicas": empresas,
            "anios_disponibles": anios,
            "caso_cobra_monto_defraudado": "RD$15,000,000,000+",
            "caso_cobra_imputados": len(CASO_SENASA["imputados"]),
        }
    finally:
        conn.close()


@router.get("/contratos")
def listar_contratos(
    anio: Optional[int] = None,
    empresa: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
):
    conn = get_conn()
    try:
        conditions = ["valor_contratado > 0"]
        if anio:
            conditions.append(f"anio = {anio}")
        if empresa:
            emp_safe = empresa.replace("'", "''")
            conditions.append(f"empresa LIKE '%{emp_safe}%'")
        where = "WHERE " + " AND ".join(conditions)
        count_row = conn.execute(f"SELECT COUNT(*) FROM contratos_seguros {where}").fetchone()[0]
        offset = (page - 1) * size
        rows = conn.execute(f"""
            SELECT codigo_contrato, estado, fecha_adjudicacion, valor_contratado,
                   moneda, objeto, rpe, empresa, anio
            FROM contratos_seguros {where}
            ORDER BY valor_contratado DESC
            LIMIT {size} OFFSET {offset}
        """).fetchall()
        return {"total": count_row, "page": page, "size": size, "results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/top-aseguradoras")
def top_aseguradoras(anio: Optional[int] = None):
    conn = get_conn()
    try:
        year_filter = f"AND anio = {anio}" if anio else "AND anio IS NOT NULL"
        rows = conn.execute(f"""
            SELECT
                empresa,
                COUNT(*)                        AS num_contratos,
                ROUND(SUM(valor_contratado), 0) AS monto_total,
                ROUND(AVG(valor_contratado), 0) AS monto_promedio,
                MAX(valor_contratado)           AS contrato_max,
                MIN(anio)                       AS primer_anio,
                MAX(anio)                       AS ultimo_anio
            FROM contratos_seguros
            WHERE valor_contratado > 0
              AND empresa != ''
              {year_filter}
            GROUP BY empresa
            ORDER BY monto_total DESC
            LIMIT 50
        """).fetchall()
        return {"results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/por-institucion")
def por_institucion(anio: Optional[int] = None):
    conn = get_conn()
    try:
        year_filter = f"AND anio = {anio}" if anio else "AND anio IS NOT NULL"
        rows = conn.execute(f"""
            SELECT
                rpe                             AS institucion_rpe,
                COUNT(*)                        AS num_contratos,
                ROUND(SUM(valor_contratado), 0) AS monto_total,
                COUNT(DISTINCT empresa)         AS empresas_distintas,
                MAX(valor_contratado)           AS contrato_max,
                MAX(anio)                       AS ultimo_anio
            FROM contratos_seguros
            WHERE valor_contratado > 0
              AND rpe IS NOT NULL AND rpe != ''
              {year_filter}
            GROUP BY rpe
            ORDER BY monto_total DESC
            LIMIT 50
        """).fetchall()
        return {"results": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/caso-senasa")
def caso_senasa():
    return {
        "caso": CASO_SENASA,
        "instituciones_sector": INSTITUCIONES_SECTOR,
    }
