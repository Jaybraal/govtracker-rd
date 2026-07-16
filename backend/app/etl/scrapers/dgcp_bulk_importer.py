"""
Importador masivo de Datos Abiertos de la DGCP publicados en datos.gob.do.

Fuente oficial: Dirección General de Contrataciones Públicas (DGCP), licencia ODbL,
catalogados en el Portal Nacional de Datos Abiertos (datos.gob.do / OGTIC).

Datasets usados (descargados a app/data/dgcp_bulk/):
  - proveedores-del-estado.csv     Registro de Proveedores del Estado (RPE), 2005-2025
  - adjudicaciones-secp.csv        Adjudicaciones del Sistema Electrónico de
                                   Contrataciones Públicas (SECP), 2015-2025
  - datos-procesos-publicados.csv  Procesos publicados en el SECP — se usa SOLO para
                                   resolver el nombre oficial de la institución a partir
                                   de las siglas que aparecen como prefijo del código
                                   (ej. "MINERD-2025-01324" -> Ministerio de Educación)

Reemplaza al endpoint en vivo de api.dgcp.gob.do (NXDOMAIN, no operativo) como fuente
de Contratos y Empresas: son los mismos datos, publicados directamente por DGCP en
formato de descarga masiva.
"""
import csv
import os
import re
import shutil
import tempfile
from datetime import datetime

import httpx
from loguru import logger
from sqlalchemy import text

from ...core.database import SessionLocal, engine
from ...models.company import Company, SupplierDisqualification
from ...models.institution import Institution, InstitutionType
from ...models.contract import Contract, ContractStatus

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "dgcp_bulk"))
PROVEEDORES_CSV = os.path.join(DATA_DIR, "proveedores-del-estado.csv")
INHABILITADOS_CSV = os.path.join(DATA_DIR, "proveedores-del-estado-inhabilitados.csv")
ADJUDICACIONES_CSV = os.path.join(DATA_DIR, "adjudicaciones-secp.csv")
PROCESOS_CSV = os.path.join(DATA_DIR, "datos-procesos-publicados.csv")

FUENTE_PROVEEDORES = "DGCP — Registro de Proveedores del Estado, datos.gob.do (licencia ODbL)"
URL_PROVEEDORES = "https://www.dgcp.gob.do/new_dgcp/documentos/da/actualizados/proveedores-del-estado.csv"
FUENTE_ADJUDICACIONES = "DGCP — Adjudicaciones SECP, datos.gob.do (licencia ODbL)"
URL_ADJUDICACIONES = "https://www.dgcp.gob.do/new_dgcp/documentos/da/actualizados/adjudicaciones-secp.csv"
# URLs inferidas por el mismo patrón de nombre de archivo que las dos de arriba
# (que sí están verificadas y documentadas desde la sesión 2026-06-07). NO se
# pudieron confirmar en esta sesión por falta de acceso a red en el entorno —
# verificar con `curl -I` antes de confiar en ellas en producción.
URL_PROCESOS = "https://www.dgcp.gob.do/new_dgcp/documentos/da/actualizados/datos-procesos-publicados.csv"
URL_INHABILITADOS = "https://www.dgcp.gob.do/new_dgcp/documentos/da/actualizados/proveedores-del-estado-inhabilitados.csv"

BATCH_SIZE = 5000

ESTADO_MAP = {
    "Cerrado": ContractStatus.COMPLETADO,
    "Activo": ContractStatus.ACTIVO,
    "Cancelado": ContractStatus.CANCELADO,
    "Anulado": ContractStatus.CANCELADO,
    "Suspendido": ContractStatus.SUSPENDIDO,
    "Rescindido": ContractStatus.EN_LITIGIO,
    "Modificado": ContractStatus.ACTIVO,
    "Flujo en aprobación": ContractStatus.ACTIVO,
    "Enviado al proveedor": ContractStatus.ACTIVO,
    "Expirado": ContractStatus.COMPLETADO,
    "Pendiente de aprobación": ContractStatus.ACTIVO,
}

INSTITUTION_TYPE_RULES = [
    (re.compile(r'^Ministerio\b', re.I), InstitutionType.MINISTERIO),
    (re.compile(r'^(Ayuntamiento|Junta (Distrital|Municipal))\b', re.I), InstitutionType.MUNICIPIO),
    (re.compile(r'^(Tribunal|Procuradur[ií]a|Juzgado|Corte)\b', re.I), InstitutionType.PODER_JUDICIAL),
    (re.compile(r'^(C[áa]mara de Diputados|Senado|Congreso)\b', re.I), InstitutionType.CONGRESO),
    (re.compile(r'^(Empresa|Corporaci[oó]n|Refiner[ií]a)\b', re.I), InstitutionType.EMPRESA_PUBLICA),
    (re.compile(r'^(Instituto|Direcci[oó]n|Consejo|Comisi[oó]n|Superintendencia|Servicio|Oficina|Junta|Despacho|Fondo|Defensor[ií]a)\b', re.I), InstitutionType.ORGANISMO_AUTONOMO),
]


def _classify_institution(nombre: str) -> InstitutionType:
    for pattern, tipo in INSTITUTION_TYPE_RULES:
        if pattern.search(nombre):
            return tipo
    return InstitutionType.OTRO


def _siglas(codigo: str) -> str:
    return (codigo or "").split("-", 1)[0].strip()


def _clean(val):
    val = (val or "").strip()
    return val if val and val.upper() != "N/A" else None


def _first_valid(*vals):
    for v in vals:
        c = _clean(v)
        if c:
            return c
    return None


def _parse_monto(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _parse_date(val):
    val = _clean(val)
    if not val:
        return None
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


# ─── Fase 1: Empresas (Registro de Proveedores del Estado) ──────────────────

def import_providers() -> int:
    """Devuelve la cantidad de proveedores NUEVOS (RPE que no existían en la
    BD antes de esta corrida) — no el total de filas procesadas del CSV.
    Antes devolvía el total procesado, que con un CSV de 132K filas siempre
    se reportaba como "132188 nuevos" aunque no hubiera ninguno realmente
    nuevo, inflando la señal de "esto cambió" que necesita la detección
    temprana para saber si vale la pena re-escanear."""
    logger.info("DGCP bulk: importando proveedores del Estado (RPE) → empresas...")
    sql = text("""
        INSERT OR IGNORE INTO empresas
            (rpe, rnc, nombre, tipo_empresa, telefono, email, direccion,
             provincia, pais, activo, total_contratos, total_monto_recibido,
             total_instituciones, indice_concentracion, created_at)
        VALUES (:rpe, :rnc, :nombre, :tipo_empresa, :telefono, :email, :direccion,
                :provincia, :pais, :activo, 0, 0, 0, 0, CURRENT_TIMESTAMP)
    """)
    with engine.begin() as conn:
        existing_rpes = {r[0] for r in conn.execute(text("SELECT rpe FROM empresas WHERE rpe IS NOT NULL")).all()}

    batch, seen_rpe = [], set()
    total = nuevos = 0
    with open(PROVEEDORES_CSV, encoding="utf-8-sig") as f, engine.begin() as conn:
        for row in csv.DictReader(f):
            rpe = _clean(row.get("RPE"))
            nombre = _clean(row.get("RAZON_SOCIAL"))
            if not rpe or not nombre or rpe in seen_rpe:
                continue
            seen_rpe.add(rpe)
            if rpe not in existing_rpes:
                nuevos += 1

            tipo_doc = _clean(row.get("TIPO_DOCUMENTO"))
            numero_doc = _clean(row.get("NUMERO_DOCUMENTO"))
            rnc = numero_doc if tipo_doc == "RNC" else None

            batch.append({
                "rpe": rpe,
                "rnc": rnc,
                "nombre": nombre[:500],
                "tipo_empresa": (_clean(row.get("FORMA_JURIDICA")) or "")[:100] or None,
                "telefono": _first_valid(row.get("TELEFONO_COMERCIAL"), row.get("CELULAR_COMERCIAL")),
                "email": _first_valid(row.get("CORREO_COMERCIAL"), row.get("CORREO_NOTIFICACIONES")),
                "direccion": _clean(row.get("DIRECCION")),
                "provincia": _clean(row.get("PROVINCIA")),
                "pais": _clean(row.get("PAIS")),  # NULL si el CSV no lo trae — no asumir "República Dominicana"
                "activo": 1 if _clean(row.get("ESTADO_RPE")) == "Activo" else 0,
            })
            if len(batch) >= BATCH_SIZE:
                conn.execute(sql, batch)
                total += len(batch)
                logger.info(f"  proveedores: {total} procesados...")
                batch = []
        if batch:
            conn.execute(sql, batch)
            total += len(batch)
    logger.info(f"DGCP bulk: {total} proveedores procesados ({nuevos} nuevos, RPE únicos)")
    return nuevos


# ─── Fase 1b: Representantes/contactos registrados en el RPE ────────────────

def import_representantes() -> int:
    """
    El RPE (proveedores-del-estado.csv) trae, para cada proveedor, un contacto
    registrado ante el Estado: CONTACTO (nombre), POSICION_CONTACTO (cargo:
    Representante, Gerente, Presidente, etc.), TELEFONO_CONTACTO/CELULAR_CONTACTO
    y CORREO_CONTACTO. Es la única fuente pública gratuita de "representante
    legal" disponible en bulk (DGII no publica esto). Una fila por empresa.

    Solo inserta para empresas que TODAVÍA no tienen representante registrado
    (antes esta función se saltaba por completo si la tabla ya tenía alguna
    fila, lo que significaba que un proveedor nuevo aparecido en un CSV
    re-descargado nunca recibía su representante legal — y por lo tanto nunca
    entraba al cruce de conflicto de interés contra legisladores).
    """
    logger.info("DGCP bulk: importando representantes/contactos (RPE) → representantes_legales...")

    with engine.begin() as conn:
        rpe_to_id = dict(conn.execute(
            text("SELECT rpe, id FROM empresas WHERE rpe IS NOT NULL AND rpe != ''")
        ).all())
        ya_tienen_rep = {row[0] for row in conn.execute(
            text("SELECT DISTINCT company_id FROM representantes_legales")
        ).all()}

    sql = text("""
        INSERT INTO representantes_legales
            (company_id, nombre, cedula, cargo, email, telefono, activo, created_at)
        VALUES (:company_id, :nombre, NULL, :cargo, :email, :telefono, 1, CURRENT_TIMESTAMP)
    """)

    batch, seen_company = [], set()
    total = 0
    with open(PROVEEDORES_CSV, encoding="utf-8-sig") as f, engine.begin() as conn:
        for row in csv.DictReader(f):
            rpe = _clean(row.get("RPE"))
            company_id = rpe_to_id.get(rpe) if rpe else None
            nombre = _clean(row.get("CONTACTO"))
            if not company_id or not nombre or company_id in seen_company or company_id in ya_tienen_rep:
                continue
            seen_company.add(company_id)
            batch.append({
                "company_id": company_id,
                "nombre": nombre[:500],
                "cargo": _clean(row.get("POSICION_CONTACTO")),
                "email": _first_valid(row.get("CORREO_CONTACTO"), row.get("CORREO_NOTIFICACIONES")),
                "telefono": _first_valid(row.get("TELEFONO_CONTACTO"), row.get("CELULAR_CONTACTO")),
            })
            if len(batch) >= BATCH_SIZE:
                conn.execute(sql, batch)
                total += len(batch)
                logger.info(f"  representantes: {total} procesados...")
                batch = []
        if batch:
            conn.execute(sql, batch)
            total += len(batch)
    logger.info(f"DGCP bulk: {total} representantes/contactos importados")
    return total


# ─── Fase 2: Resolver instituciones desde siglas de códigos de proceso ───────

def build_siglas_map() -> dict:
    logger.info("DGCP bulk: construyendo mapa siglas → institución desde procesos publicados...")
    counter: dict[str, dict[str, int]] = {}
    with open(PROCESOS_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sigla = _siglas(row.get("CODIGO_PROCESO"))
            unidad = _clean(row.get("UNIDAD_COMPRA"))
            if not sigla or not unidad:
                continue
            bucket = counter.setdefault(sigla, {})
            bucket[unidad] = bucket.get(unidad, 0) + 1
    siglas_map = {sigla: max(names, key=names.get) for sigla, names in counter.items()}
    logger.info(f"DGCP bulk: {len(siglas_map)} siglas de institución resueltas")
    return siglas_map


def ensure_institutions(db, siglas_map: dict) -> dict:
    existing = {i.siglas.strip().upper(): i.id for i in db.query(Institution).all() if i.siglas}
    sigla_to_id, created = {}, 0
    for sigla, nombre in siglas_map.items():
        key = sigla.upper()
        if key in existing:
            sigla_to_id[sigla] = existing[key]
            continue
        inst = Institution(nombre=nombre[:500], siglas=sigla[:50], tipo=_classify_institution(nombre))
        db.add(inst)
        db.flush()
        existing[key] = inst.id
        sigla_to_id[sigla] = inst.id
        created += 1
    db.commit()
    logger.info(f"DGCP bulk: {created} instituciones nuevas creadas ({len(sigla_to_id)} siglas resueltas en total)")
    return sigla_to_id


# ─── Fase 3: Contratos (Adjudicaciones SECP) ─────────────────────────────────

def import_adjudicaciones(db, sigla_to_inst_id: dict) -> int:
    logger.info("DGCP bulk: importando adjudicaciones SECP → contratos...")

    rpe_to_id, rnc_to_id = {}, {}
    for c in db.query(Company.id, Company.rpe, Company.rnc):
        if c.rpe:
            rpe_to_id[c.rpe] = c.id
        if c.rnc:
            rnc_to_id[c.rnc] = c.id

    existing_numeros = {r[0] for r in db.query(Contract.numero_contrato).all()}

    # NOTA: monto_pagado, tiene_adendas, num_adendas, incremento_porcentual, retraso_dias
    # y financiado_prestamo se dejan en NULL (no en 0/false): adjudicaciones-secp.csv no
    # contiene esa información, y afirmar "0" sería tan fabricación como inventar un número
    # ("omitir en vez de inventar"). monto_actual también queda NULL — el dataset solo trae
    # un valor (VALOR_CONTRATADO) y no permite distinguir "monto original" de "monto tras adendas".
    sql = text("""
        INSERT OR IGNORE INTO contratos
            (numero_contrato, institution_id, company_id, descripcion, objeto, estado,
             monto_original, monto_actual, monto_pagado, moneda, fecha_firma,
             tiene_adendas, num_adendas, incremento_porcentual, retraso_dias,
             financiado_prestamo, es_mayor_100m, fuente, url_fuente, created_at)
        VALUES (:numero_contrato, :institution_id, :company_id, :objeto, :objeto, :estado,
                :monto, NULL, NULL, :moneda, :fecha_firma,
                NULL, NULL, NULL, NULL, NULL, :es_mayor_100m, :fuente, :url_fuente, CURRENT_TIMESTAMP)
    """)

    batch, seen_numeros = [], set()
    total = skipped_no_company = skipped_no_institution = 0
    with open(ADJUDICACIONES_CSV, encoding="utf-8-sig") as f, engine.begin() as conn:
        for row in csv.DictReader(f):
            numero = _clean(row.get("CODIGO_CONTRATO"))
            if not numero or numero in existing_numeros or numero in seen_numeros:
                continue
            seen_numeros.add(numero)

            institution_id = sigla_to_inst_id.get(_siglas(numero))
            if not institution_id:
                skipped_no_institution += 1
                continue

            rpe = _clean(row.get("RPE"))
            rnc = _clean(row.get("NUMERO_DOCUMENTO"))
            company_id = (rpe_to_id.get(rpe) if rpe else None) or (rnc_to_id.get(rnc) if rnc else None)
            if not company_id:
                skipped_no_company += 1
                continue

            monto = _parse_monto(row.get("VALOR_CONTRATADO"))
            estado = ESTADO_MAP.get(_clean(row.get("ESTADO_CONTRATO")), ContractStatus.ACTIVO)
            fecha = _parse_date(row.get("FECHA_ADJUDICACION")) or _parse_date(row.get("FECHA_CREACION_CONTRATO"))
            objeto = _clean(row.get("OBJETO_CONTRATO"))

            batch.append({
                "numero_contrato": numero[:200],
                "institution_id": institution_id,
                "company_id": company_id,
                "objeto": objeto,
                "estado": estado.name,
                "monto": monto,
                "moneda": (_clean(row.get("MONEDA")) or "DOP")[:10],
                "fecha_firma": fecha.isoformat() if fecha else None,
                "es_mayor_100m": 1 if monto >= 100_000_000 else 0,
                "fuente": FUENTE_ADJUDICACIONES,
                "url_fuente": URL_ADJUDICACIONES,
            })
            if len(batch) >= BATCH_SIZE:
                conn.execute(sql, batch)
                total += len(batch)
                logger.info(f"  adjudicaciones: {total} importados "
                            f"(sin empresa: {skipped_no_company}, sin institución: {skipped_no_institution})...")
                batch = []
        if batch:
            conn.execute(sql, batch)
            total += len(batch)

    logger.info(f"DGCP bulk: {total} contratos importados "
                f"(omitidos sin empresa resoluble: {skipped_no_company}, sin institución: {skipped_no_institution})")
    return total


# ─── Fase 4: Recalcular estadísticas agregadas ───────────────────────────────

# ─── Fase 4: Proveedores del Estado Inhabilitados (registro oficial DGCP/SECP) ──

def import_inhabilitados(db) -> int:
    """Importa el registro oficial de Proveedores del Estado Inhabilitados,
    cruzando por RPE contra las empresas ya importadas. Cada fila representa
    un evento de sanción real (RPE + fecha + motivo) tal como lo publica DGCP —
    se deduplican únicamente los registros idénticos (mismo RPE/fecha/motivo
    re-anotados con distinta hora), preservando sanciones distintas en el tiempo.

    Antes solo dedupaba DENTRO del CSV de la corrida actual, sin mirar lo que
    ya había en la BD — al volver a llamarse (p.ej. desde la detección
    temprana, pensada para correr repetidas veces) duplicaba los ~2,000
    eventos de inhabilitación en cada corrida. Ahora también excluye los que
    ya existen en `proveedores_inhabilitados`."""
    if not os.path.exists(INHABILITADOS_CSV):
        logger.warning(f"  inhabilitados: no se encontró {INHABILITADOS_CSV}, se omite")
        return 0
    logger.info("DGCP bulk: importando proveedores inhabilitados (registro oficial DGCP/SECP)...")

    rpe_to_company = {rpe: cid for cid, rpe in db.query(Company.id, Company.rpe).filter(Company.rpe.isnot(None)).all()}
    # Vía ORM (no SQL crudo) para que SQLAlchemy aplique el result processor
    # del tipo DateTime y devuelva objetos datetime reales — comparar contra
    # un string crudo de sqlite3 (formato con espacio/microsegundos) nunca
    # calzaría con el .isoformat() de un datetime recién parseado del CSV.
    ya_existen = {
        (rpe, fecha.isoformat() if fecha else None, motivo)
        for rpe, fecha, motivo in db.query(
            SupplierDisqualification.rpe,
            SupplierDisqualification.fecha_inhabilitacion,
            SupplierDisqualification.motivo,
        ).all()
    }

    sql = text("""
        INSERT INTO proveedores_inhabilitados
            (rpe, company_id, motivo, fecha_inhabilitacion, fecha_habilitacion,
             oficio_inhabilitacion, url_certificacion, fuente, url_fuente, created_at)
        VALUES (:rpe, :company_id, :motivo, :fecha_inhabilitacion, :fecha_habilitacion,
                :oficio_inhabilitacion, :url_certificacion, :fuente, :url_fuente, CURRENT_TIMESTAMP)
    """)
    seen, batch = set(), []
    vinculados = 0
    with open(INHABILITADOS_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rpe = _clean(row.get("RPE"))
            motivo = _clean(row.get("MOTIVO_INHABILITACION"))
            if not rpe or not motivo:
                continue
            fecha_inhab = _parse_date(row.get("FECHA_INHABILITACION"))
            fecha_key = fecha_inhab.isoformat() if fecha_inhab else None
            key = (rpe, fecha_key, motivo)
            if key in seen or key in ya_existen:
                continue
            seen.add(key)
            company_id = rpe_to_company.get(rpe)
            if company_id:
                vinculados += 1
            batch.append({
                "rpe": rpe,
                "company_id": company_id,
                "motivo": motivo,
                "fecha_inhabilitacion": fecha_inhab,
                "fecha_habilitacion": _parse_date(row.get("FECHA_HABILITACION")),
                "oficio_inhabilitacion": _clean(row.get("OFICIO_INHABILITACION")),
                "url_certificacion": _clean(row.get("URL_CERTIFICACION_RPE")),
                "fuente": "DGCP — Proveedores del Estado Inhabilitados (SECP)",
                "url_fuente": "https://www.dgcp.gob.do/",
            })
    if batch:
        with engine.begin() as conn:
            conn.execute(sql, batch)
    logger.info(f"DGCP bulk: {len(batch)} eventos de inhabilitación importados ({vinculados} vinculados a empresas por RPE)")
    return len(batch)


def recompute_stats(db):
    """Recalcula contadores agregados con joins indexados (evita subconsultas
    correlacionadas fila-por-fila, inviables a esta escala — 655K contratos)."""
    logger.info("DGCP bulk: recalculando estadísticas de empresas e instituciones...")
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_contratos_company_id ON contratos(company_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_contratos_institution_id ON contratos(institution_id)"))
    db.execute(text("""
        UPDATE empresas SET
            total_contratos = agg.cnt,
            total_monto_recibido = agg.monto,
            total_instituciones = agg.insts
        FROM (
            SELECT company_id, COUNT(*) AS cnt, SUM(monto_original) AS monto,
                   COUNT(DISTINCT institution_id) AS insts
            FROM contratos GROUP BY company_id
        ) AS agg
        WHERE empresas.id = agg.company_id
    """))
    # indice_concentracion = % del monto total de la empresa que proviene de su
    # única institución más fuerte (proxy real de dependencia/captura institucional)
    db.execute(text("""
        UPDATE empresas SET indice_concentracion = agg.pct
        FROM (
            SELECT cit.company_id AS cid,
                   MAX(cit.monto_inst) * 100.0 / SUM(cit.monto_inst) AS pct
            FROM (
                SELECT company_id, institution_id, SUM(monto_original) AS monto_inst
                FROM contratos GROUP BY company_id, institution_id
            ) cit
            GROUP BY cit.company_id
        ) AS agg
        WHERE empresas.id = agg.cid
    """))
    db.execute(text("""
        UPDATE instituciones SET
            total_contratos = agg.cnt,
            total_monto_contratos = agg.monto
        FROM (
            SELECT institution_id, COUNT(*) AS cnt, SUM(monto_original) AS monto
            FROM contratos GROUP BY institution_id
        ) AS agg
        WHERE instituciones.id = agg.institution_id
    """))
    db.commit()
    logger.info("DGCP bulk: estadísticas recalculadas")


_DOWNLOADS = {
    "proveedores": (URL_PROVEEDORES, PROVEEDORES_CSV),
    "adjudicaciones": (URL_ADJUDICACIONES, ADJUDICACIONES_CSV),
    "procesos": (URL_PROCESOS, PROCESOS_CSV),
    "inhabilitados": (URL_INHABILITADOS, INHABILITADOS_CSV),
}


def download_latest_csvs(timeout: float = 120.0) -> dict:
    """
    Descarga la versión más reciente de cada CSV oficial directamente desde
    dgcp.gob.do (las URLs "/actualizados/..." — el propio DGCP las refresca
    en cada corte de datos abiertos, sin necesidad de bajarlas a mano cada
    vez). Es lo que convierte la carga masiva (antes 100% manual) en algo que
    se puede re-ejecutar para detectar contratos/proveedores nuevos.

    No asume que la descarga trajo algo nuevo ni que el archivo remoto es
    válido: si la respuesta no parece un CSV, o la descarga falla, conserva
    el archivo local existente y reporta el error en vez de sobreescribir con
    basura. Devuelve por archivo: "actualizado" | "sin_cambios" | "error: ...".
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    resultados = {}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for nombre, (url, destino) in _DOWNLOADS.items():
            try:
                resp = client.get(url)
                resp.raise_for_status()
                contenido = resp.content
                if not contenido or b"," not in contenido[:2000]:
                    resultados[nombre] = "error: la respuesta no parece un CSV"
                    logger.warning(f"DGCP download {nombre}: respuesta no parece CSV, se conserva el archivo local")
                    continue
                if os.path.exists(destino) and open(destino, "rb").read() == contenido:
                    resultados[nombre] = "sin_cambios"
                    continue
                with tempfile.NamedTemporaryFile(dir=DATA_DIR, delete=False) as tmp:
                    tmp.write(contenido)
                    tmp_path = tmp.name
                shutil.move(tmp_path, destino)
                resultados[nombre] = "actualizado"
                logger.info(f"DGCP download {nombre}: actualizado ({len(contenido)} bytes)")
            except Exception as e:
                resultados[nombre] = f"error: {e}"
                logger.warning(f"DGCP download {nombre} falló, se conserva el archivo local si existe: {e}")
    return resultados


def run_dgcp_bulk_import(descargar: bool = False) -> dict:
    """Ejecuta el pipeline completo: (descarga opcional) → proveedores →
    instituciones → adjudicaciones → stats. Es seguro llamarlo repetidas
    veces: cada fase usa upserts/dedup por clave de negocio (RPE, RNC,
    numero_contrato), así que una corrida sobre un CSV ya importado no
    duplica nada y una corrida sobre un CSV con filas nuevas solo agrega
    esas filas."""
    descargas = download_latest_csvs() if descargar else None

    if not (os.path.exists(PROVEEDORES_CSV) and os.path.exists(ADJUDICACIONES_CSV) and os.path.exists(PROCESOS_CSV)):
        raise FileNotFoundError(
            f"Faltan datasets en {DATA_DIR}. Descargar de datos.gob.do: "
            "proveedores-del-estado.csv, adjudicaciones-secp.csv, datos-procesos-publicados.csv"
        )

    n_providers = import_providers()
    n_representantes = import_representantes()

    siglas_map = build_siglas_map()
    db = SessionLocal()
    try:
        sigla_to_inst_id = ensure_institutions(db, siglas_map)
        n_contracts = import_adjudicaciones(db, sigla_to_inst_id)
        n_inhabilitados = import_inhabilitados(db)
        recompute_stats(db)
    finally:
        db.close()

    result = {
        "proveedores": n_providers, "representantes": n_representantes, "contratos": n_contracts,
        "instituciones_resueltas": len(sigla_to_inst_id), "inhabilitados": n_inhabilitados,
        "descargas": descargas,
    }
    logger.info(f"DGCP bulk import completado: {result}")
    return result


if __name__ == "__main__":
    run_dgcp_bulk_import()
