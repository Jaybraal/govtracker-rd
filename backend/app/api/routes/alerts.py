from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.alert import Alert, AlertSeverity, AlertType
from ...models.contract import Contract
from ...models.company import Company, SupplierDisqualification
from ...core.config import settings

router = APIRouter(prefix="/alerts", tags=["Alertas"])


@router.get("/")
def list_alerts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
    severidad: Optional[str] = None,
    tipo: Optional[str] = None,
    revisada: Optional[bool] = None,
    descartada: bool = False,
):
    q = db.query(Alert).filter(Alert.descartada == descartada)
    if severidad:
        q = q.filter(Alert.severidad == severidad)
    if tipo:
        q = q.filter(Alert.tipo == tipo)
    if revisada is not None:
        q = q.filter(Alert.revisada == revisada)
    total = q.count()
    items = q.order_by(desc(Alert.created_at)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize(a) for a in items],
    }


@router.get("/stats")
def alert_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Alert.id)).filter(Alert.descartada == False).scalar()
    no_revisadas = db.query(func.count(Alert.id)).filter(
        Alert.revisada == False, Alert.descartada == False
    ).scalar()
    criticas = db.query(func.count(Alert.id)).filter(
        Alert.severidad == AlertSeverity.CRITICA, Alert.descartada == False
    ).scalar()
    por_tipo = db.query(
        Alert.tipo, func.count(Alert.id).label("cnt")
    ).filter(Alert.descartada == False).group_by(Alert.tipo).all()
    return {
        "total": total,
        "no_revisadas": no_revisadas,
        "criticas": criticas,
        "por_tipo": [{"tipo": r.tipo, "cantidad": r.cnt} for r in por_tipo],
    }


@router.post("/scan")
def run_alert_scan(db: Session = Depends(get_db)):
    """Ejecuta el scanner de alertas sobre los datos actuales."""
    generated = _run_scan(db)
    return {"message": f"{generated} alertas generadas", "count": generated}


@router.patch("/{alert_id}/review")
def review_alert(
    alert_id: int,
    notas: str = Body("", embed=True),
    db: Session = Depends(get_db),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(404, "Alerta no encontrada")
    alert.revisada = True
    alert.notas_revision = notas
    db.commit()
    return {"ok": True}


@router.patch("/{alert_id}/discard")
def discard_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.descartada = True
        db.commit()
    return {"ok": True}


def _run_scan(db: Session) -> int:
    count = 0

    # 1. Contratos > RD$100M con contratación directa
    risky = db.query(Contract).filter(
        Contract.monto_original >= settings.ALERT_CONTRACT_THRESHOLD,
        Contract.modalidad == "contratacion_directa",
    ).all()
    for c in risky:
        if not _alert_exists(db, AlertType.CONTRATO_GRANDE, c.id):
            db.add(Alert(
                tipo=AlertType.CONTRATO_GRANDE,
                severidad=AlertSeverity.ALTA,
                titulo=f"Contrato directo >{_fmt(settings.ALERT_CONTRACT_THRESHOLD)}",
                descripcion=f"Contrato {c.numero_contrato} por {_fmt(c.monto_original)} via contratación directa",
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=c.monto_original,
                datos_extra={},
            ))
            count += 1

    # 2. Contratos con incremento > 25%
    for c in db.query(Contract).filter(Contract.incremento_porcentual >= settings.ALERT_PRICE_INCREASE_PCT).all():
        if not _alert_exists(db, AlertType.INCREMENTO_PRECIO, c.id):
            db.add(Alert(
                tipo=AlertType.INCREMENTO_PRECIO,
                severidad=AlertSeverity.ALTA,
                titulo=f"Incremento {c.incremento_porcentual:.1f}% en contrato",
                descripcion=f"Contrato {c.numero_contrato} incrementó de {_fmt(c.monto_original)} a {_fmt(c.monto_actual)}",
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=(c.monto_actual or 0) - c.monto_original,
                datos_extra={},
            ))
            count += 1

    # 3. Contratos con demasiadas adendas
    for c in db.query(Contract).filter(Contract.num_adendas >= settings.ALERT_ADDENDUM_COUNT).all():
        if not _alert_exists(db, AlertType.MUCHAS_ADENDAS, c.id):
            db.add(Alert(
                tipo=AlertType.MUCHAS_ADENDAS,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Contrato con {c.num_adendas} adendas",
                descripcion=f"Contrato {c.numero_contrato} acumula {c.num_adendas} modificaciones",
                entidad_tipo="contrato", entidad_id=c.id,
                monto_involucrado=c.monto_actual,
                datos_extra={},
            ))
            count += 1

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
            db.add(Alert(
                tipo=AlertType.EMPRESA_CONCENTRADA,
                severidad=AlertSeverity.MEDIA,
                titulo=f"Empresa con {r.cnt} contratos en misma institución",
                descripcion=f"{comp.nombre} tiene {r.cnt} contratos totalizando {_fmt(r.monto)}",
                entidad_tipo="empresa", entidad_id=r.company_id,
                monto_involucrado=r.monto,
                datos_extra={},
            ))
            count += 1

    # 5. Anomalías estadísticas de monto (contratos cuyo valor es órdenes de
    #    magnitud mayor a lo plausible — p.ej. RD$46,000M por "Servicios" de
    #    vigilancia — verificados byte-a-byte contra el CSV oficial de DGCP;
    #    casi con certeza errores de digitación de la institución, no del dato)
    for c in db.query(Contract).filter(Contract.monto_original >= settings.ALERT_ANOMALY_THRESHOLD).all():
        if not _alert_exists(db, AlertType.ANOMALIA_MONTO, c.id):
            db.add(Alert(
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
            ))
            count += 1

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
                from ...models.institution import Institution
                inst = db.query(Institution).get(top.institution_id)
                if inst:
                    inst_nombre = inst.siglas or inst.nombre
            db.add(Alert(
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
            ))
            count += 1

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
            db.add(Alert(
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
            ))
            count += 1

    db.commit()
    return count


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


def _serialize(a: Alert) -> dict:
    return {
        "id": a.id, "tipo": a.tipo, "severidad": a.severidad,
        "titulo": a.titulo, "descripcion": a.descripcion,
        "entidad_tipo": a.entidad_tipo, "entidad_id": a.entidad_id,
        "entidad_nombre": a.entidad_nombre, "monto_involucrado": a.monto_involucrado,
        "revisada": a.revisada, "descartada": a.descartada,
        "notas_revision": a.notas_revision, "datos_extra": a.datos_extra,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
