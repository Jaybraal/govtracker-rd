"""
Scanner de alertas — antes vivía como función privada dentro de la ruta
`/alerts/scan`. Se extrae a servicio para poder invocarlo también desde el
pipeline de detección temprana (`/etl/deteccion-temprana`), que lo corre
automáticamente después de cada actualización de datos en vez de depender
de que alguien lo dispare manualmente desde el panel de alertas.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..models.alert import Alert, AlertType, AlertSeverity
from ..models.contract import Contract
from ..models.company import Company, SupplierDisqualification, LegalRepresentative
from ..models.legislator import Legislator
from ..core.config import settings

import sqlite3
import unicodedata
import re
import hashlib
from pathlib import Path

from loguru import logger

NOMINAS_DB_DEFAULT = Path(__file__).parent.parent.parent.parent / "data" / "nominas.db"


def _norm_nombre(s: str) -> str:
    n = (s or "").upper().strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^A-Z\s]", "", n)
    return n.strip()


def _scan_nomina_doble_cobro(db: Session, nominas_db_path: Path = NOMINAS_DB_DEFAULT) -> list[Alert]:
    """Misma persona cobrando en >1 institución el mismo mes. Reutiliza el
    heurístico de confianza ya validado en producción por
    `api/routes/nominas.py::doble_cobro` (nombre normalizado más largo =
    más específico = menos probable que sea coincidencia de homónimos) —
    pero antes esta lógica nunca alimentaba la tabla Alert. Solo genera
    alerta para confianza ALTA: es una regla nueva, hay que estrenarla con
    el listón más exigente, no con el más ruidoso.

    Tolera que `nominas.db` no exista (2.2GB, no vive en CI) — devuelve
    lista vacía en vez de romper toda la corrida."""
    if not Path(nominas_db_path).exists():
        return []

    try:
        conn = sqlite3.connect(str(nominas_db_path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT nombre, MIN(nombre_raw) AS nombre_raw,
                       COUNT(*) AS meses_afectados,
                       GROUP_CONCAT(DISTINCT instituciones_mes) AS instituciones,
                       ROUND(SUM(total_mes), 0) AS total_cobrado
                FROM (
                    SELECT nombre, MIN(nombre_raw) AS nombre_raw, anio, mes,
                           COUNT(DISTINCT institucion) AS num_inst,
                           GROUP_CONCAT(DISTINCT institucion) AS instituciones_mes,
                           SUM(salario) AS total_mes
                    FROM empleados
                    WHERE anio BETWEEN 2010 AND 2026
                    GROUP BY nombre, anio, mes
                    HAVING num_inst > 1 AND nombre != '' AND LENGTH(nombre) > 22
                ) sub
                GROUP BY nombre
            """).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning(
            f"nominas.db existe pero no se pudo leer ({e}) — se omite esta regla en esta corrida"
        )
        return []

    nuevas: list[Alert] = []
    for r in rows:
        # hash() de Python está aleatorizado por proceso (PYTHONHASHSEED no
        # fijado en este repo) — el cron corre en un proceso nuevo cada día,
        # así que hash() daría una clave DISTINTA para la misma persona cada
        # vez y _alert_exists nunca encontraría la alerta de la corrida
        # anterior, duplicándola para siempre. Se usa un hash estable
        # (sha256) para que la misma persona produzca siempre la misma clave.
        key = int(hashlib.sha256(r["nombre"].encode()).hexdigest()[:15], 16) % 2_000_000_000
        if _alert_exists(db, AlertType.NOMINA_DOBLE_COBRO, key):
            continue
        nuevas.append(_add(db, Alert(
            tipo=AlertType.NOMINA_DOBLE_COBRO,
            severidad=AlertSeverity.ALTA,
            titulo=f"Posible doble cobro en nómina: {r['nombre_raw']}",
            descripcion=(
                f"«{r['nombre_raw']}» aparece cobrando en {r['instituciones']} durante "
                f"{r['meses_afectados']} mes(es), por un total de {_fmt(r['total_cobrado'] or 0)} — "
                f"coincidencia por nombre, sin cédula que confirme identidad; requiere verificación "
                f"manual antes de concluir doble cobro indebido"
            ),
            entidad_tipo="persona_nomina", entidad_id=key,
            entidad_nombre=r["nombre_raw"],
            monto_involucrado=r["total_cobrado"],
            datos_extra={"instituciones": r["instituciones"], "verificado": False},
        )))
    db.commit()
    return nuevas


def run_alert_scan(db: Session) -> list[Alert]:
    """Ejecuta todas las reglas de detección sobre los datos actuales y
    devuelve solo las alertas NUEVAS creadas en esta corrida (las que ya
    existían — incluso de corridas anteriores — se omiten vía
    `_alert_exists`, así que llamar esto repetidamente es seguro)."""
    nuevas: list[Alert] = []

    # 1. Contratos > RD$100M con contratación directa
    risky = db.query(Contract).filter(
        Contract.monto_original >= settings.ALERT_CONTRACT_THRESHOLD,
        Contract.modalidad == "contratacion_directa",
    ).all()
    for c in risky:
        if not _alert_exists(db, AlertType.CONTRATO_GRANDE, c.id):
            nuevas.append(_add(db, Alert(
                tipo=AlertType.CONTRATO_GRANDE,
                severidad=AlertSeverity.ALTA,
                titulo=f"Contrato directo >{_fmt(settings.ALERT_CONTRACT_THRESHOLD)}",
                descripcion=f"Contrato {c.numero_contrato} por {_fmt(c.monto_original)} via contratación directa",
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=c.monto_original,
                datos_extra={},
            )))

    # 2. Contratos con incremento > 25%
    for c in db.query(Contract).filter(Contract.incremento_porcentual >= settings.ALERT_PRICE_INCREASE_PCT).all():
        if not _alert_exists(db, AlertType.INCREMENTO_PRECIO, c.id):
            nuevas.append(_add(db, Alert(
                tipo=AlertType.INCREMENTO_PRECIO,
                severidad=AlertSeverity.ALTA,
                titulo=f"Incremento {c.incremento_porcentual:.1f}% en contrato",
                descripcion=f"Contrato {c.numero_contrato} incrementó de {_fmt(c.monto_original)} a {_fmt(c.monto_actual)}",
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=(c.monto_actual or 0) - c.monto_original,
                datos_extra={},
            )))

    # 3. Contratos con demasiadas adendas
    for c in db.query(Contract).filter(Contract.num_adendas >= settings.ALERT_ADDENDUM_COUNT).all():
        if not _alert_exists(db, AlertType.MUCHAS_ADENDAS, c.id):
            nuevas.append(_add(db, Alert(
                tipo=AlertType.MUCHAS_ADENDAS,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Contrato con {c.num_adendas} adendas",
                descripcion=f"Contrato {c.numero_contrato} acumula {c.num_adendas} modificaciones",
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=c.monto_actual,
                datos_extra={},
            )))

    # 4. Empresas con >20 contratos en misma institución
    rows = db.query(
        Contract.company_id, Contract.institution_id,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto"),
    ).group_by(Contract.company_id, Contract.institution_id)\
     .having(func.count(Contract.id) >= settings.ALERT_COMPANY_CONTRACT_COUNT).all()
    for r in rows:
        comp = db.query(Company).get(r.company_id)
        key = r.company_id * 100000 + r.institution_id
        if comp and not _alert_exists(db, AlertType.EMPRESA_CONCENTRADA, key):
            nuevas.append(_add(db, Alert(
                tipo=AlertType.EMPRESA_CONCENTRADA,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Empresa con {r.cnt} contratos en misma institución",
                descripcion=f"{comp.nombre} tiene {r.cnt} contratos totalizando {_fmt(r.monto)}",
                entidad_tipo="empresa", entidad_id=r.company_id,
                monto_involucrado=r.monto,
                datos_extra={},
            )))

    # 5. Anomalías estadísticas de monto (contratos cuyo valor es órdenes de
    #    magnitud mayor a lo plausible — p.ej. RD$46,000M por "Servicios" de
    #    vigilancia — verificados byte-a-byte contra el CSV oficial de DGCP;
    #    casi con certeza errores de digitación de la institución, no del dato)
    for c in db.query(Contract).filter(Contract.monto_original >= settings.ALERT_ANOMALY_THRESHOLD).all():
        if not _alert_exists(db, AlertType.ANOMALIA_MONTO, c.id):
            nuevas.append(_add(db, Alert(
                tipo=AlertType.ANOMALIA_MONTO,
                severidad=AlertSeverity.CRITICA,
                titulo=f"Monto estadísticamente anómalo: {_fmt(c.monto_original)}",
                descripcion=(
                    f"Contrato {c.numero_contrato} ({c.estado.value if c.estado else '—'}) "
                    f"declara {_fmt(c.monto_original)} por «{c.objeto or c.descripcion or 'objeto no especificado'}» "
                    f"— órdenes de magnitud por encima de lo habitual; revisar si es error de digitación de la institución"
                ),
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=c.monto_original,
                datos_extra={"fuente": c.fuente, "url_fuente": c.url_fuente},
            )))

    # 6. Empresas cautivas: dependen casi por completo (>=90% del monto que
    #    reciben) de UNA sola institución, con suma relevante en juego — el
    #    patrón clásico de "empresa satélite" / contratista capturado
    for comp in db.query(Company).filter(
        Company.indice_concentracion >= settings.ALERT_CAPTIVE_CONCENTRATION_PCT,
        Company.total_monto_recibido >= settings.ALERT_CAPTIVE_MIN_MONTO,
        Company.total_contratos >= 3,
    ).all():
        if not _alert_exists(db, AlertType.EMPRESA_CAUTIVA, comp.id):
            top = db.query(Contract.institution_id, func.sum(Contract.monto_original).label("monto"))\
                    .filter(Contract.company_id == comp.id)\
                    .group_by(Contract.institution_id).order_by(desc("monto")).first()
            inst_nombre = "una institución"
            if top:
                from ..models.institution import Institution
                inst = db.query(Institution).get(top.institution_id)
                if inst:
                    inst_nombre = inst.siglas or inst.nombre
            nuevas.append(_add(db, Alert(
                tipo=AlertType.EMPRESA_CAUTIVA,
                severidad=AlertSeverity.ALTA if comp.indice_concentracion >= 98 else AlertSeverity.MEDIA,
                titulo=f"Empresa con {comp.indice_concentracion:.0f}% de su negocio en una sola institución",
                descripcion=(
                    f"{comp.nombre} recibió {_fmt(comp.total_monto_recibido)} en {comp.total_contratos} contratos, "
                    f"de los cuales {comp.indice_concentracion:.1f}% provienen de {inst_nombre} — "
                    f"posible relación de dependencia/exclusividad"
                ),
                entidad_tipo="empresa", entidad_id=comp.id,
                monto_involucrado=comp.total_monto_recibido,
                datos_extra={"indice_concentracion": comp.indice_concentracion, "total_instituciones": comp.total_instituciones},
            )))

    # 7. Contratos firmados con proveedores YA inhabilitados por DGCP — el propio
    #    órgano regulador (SECP) sancionó oficialmente a la empresa (a menudo de
    #    forma permanente, por presentar documentos falsos o incumplimiento) y,
    #    pese a ello, el Estado firmó contratos con ella en o después de esa fecha
    rows = db.query(Contract, SupplierDisqualification, Company).join(
        SupplierDisqualification, SupplierDisqualification.company_id == Contract.company_id
    ).join(Company, Company.id == Contract.company_id).filter(
        Contract.fecha_firma.isnot(None),
        SupplierDisqualification.fecha_inhabilitacion.isnot(None),
        Contract.fecha_firma >= SupplierDisqualification.fecha_inhabilitacion,
    ).all()
    # Una empresa puede tener varios eventos de sanción — nos quedamos con el
    # MÁS ANTIGUO que el contrato ya incumple (el punto más temprano en que ya
    # debió haber sido excluida) para generar UNA sola alerta por contrato
    earliest_per_contract: dict[int, tuple] = {}
    for c, d, comp in rows:
        cur = earliest_per_contract.get(c.id)
        if cur is None or d.fecha_inhabilitacion < cur[1].fecha_inhabilitacion:
            earliest_per_contract[c.id] = (c, d, comp)
    for c, d, comp in earliest_per_contract.values():
        if not _alert_exists(db, AlertType.PROVEEDOR_INHABILITADO, c.id):
            permanente = "permanentemente" in (d.motivo or "").lower()
            nuevas.append(_add(db, Alert(
                tipo=AlertType.PROVEEDOR_INHABILITADO,
                severidad=AlertSeverity.CRITICA,
                titulo="Contrato firmado con proveedor ya inhabilitado por DGCP",
                descripcion=(
                    f"{comp.nombre} firmó el contrato {c.numero_contrato} por {_fmt(c.monto_original)} "
                    f"el {c.fecha_firma.strftime('%d/%m/%Y')} — {'PERMANENTEMENTE ' if permanente else ''}"
                    f"inhabilitada por DGCP/SECP desde el {d.fecha_inhabilitacion.strftime('%d/%m/%Y')} "
                    f"({d.oficio_inhabilitacion or 'resolución oficial'}: «{(d.motivo or '')[:200]}»)"
                ),
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=c.monto_original,
                datos_extra={
                    "company_id": comp.id, "rpe": d.rpe,
                    "motivo_inhabilitacion": d.motivo,
                    "fecha_inhabilitacion": d.fecha_inhabilitacion.isoformat(),
                    "oficio": d.oficio_inhabilitacion,
                    "fuente": d.fuente, "url_fuente": d.url_fuente,
                },
            )))

    # 8. Legisladores en ejercicio cuyo nombre coincide con el de un
    #    representante legal de una empresa contratista del Estado. Es una
    #    coincidencia POR NOMBRE (el SIL no publica cédula del legislador),
    #    no una identidad confirmada — requiere verificación manual antes de
    #    imputar conflicto de interés a la persona.
    for leg in db.query(Legislator).filter(Legislator.total_contratos_relacionados > 0).all():
        if not _alert_exists(db, AlertType.POSIBLE_CONFLICTO, leg.id):
            reps = db.query(LegalRepresentative).filter(
                func.upper(LegalRepresentative.nombre) == func.upper(leg.nombre_completo)
            ).all()
            empresas = ", ".join(sorted({r.company.nombre for r in reps if r.company})[:3])
            nuevas.append(_add(db, Alert(
                tipo=AlertType.POSIBLE_CONFLICTO,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Legislador con nombre coincidente a representante legal de contratista",
                descripcion=(
                    f"El nombre «{leg.nombre_completo}» ({leg.funcion or 'legislador'}, {leg.partido_siglas or '—'}) "
                    f"coincide con el de un representante legal en {empresas or 'empresa(s) contratista(s)'}, "
                    f"con {leg.total_contratos_relacionados} contrato(s) del Estado por "
                    f"{_fmt(leg.total_monto_relacionado)} — coincidencia por nombre, sin cédula que confirme "
                    f"identidad; requiere verificación manual antes de concluir conflicto de interés"
                ),
                entidad_tipo="legislador", entidad_id=leg.id,
                monto_involucrado=leg.total_monto_relacionado,
                datos_extra={"camara": leg.camara.value if leg.camara else None, "verificado": False},
            )))

    nuevas.extend(_scan_nomina_doble_cobro(db))

    db.commit()
    return nuevas


def _add(db: Session, alert: Alert) -> Alert:
    db.add(alert)
    return alert


def _alert_exists(db: Session, tipo: AlertType, entidad_id: int) -> bool:
    return db.query(Alert).filter(
        Alert.tipo == tipo,
        Alert.entidad_id == entidad_id,
        Alert.descartada == False,
    ).first() is not None


def _fmt(monto: float) -> str:
    if monto >= 1_000_000_000:
        return f"RD${monto/1_000_000_000:.1f}B"
    if monto >= 1_000_000:
        return f"RD${monto/1_000_000:.1f}M"
    return f"RD${monto:,.0f}"
