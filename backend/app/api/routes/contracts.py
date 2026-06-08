from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from typing import Optional, List
from ...core.database import get_db
from ...models.contract import Contract, ContractStatus, ModalidadCompra
from ...models.company import Company
from ...models.institution import Institution

router = APIRouter(prefix="/contracts", tags=["Contratos"])


@router.get("/")
def list_contracts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
    institution_id: Optional[int] = None,
    company_id: Optional[int] = None,
    modalidad: Optional[str] = None,
    estado: Optional[str] = None,
    monto_min: Optional[float] = None,
    monto_max: Optional[float] = None,
    financiado_prestamo: Optional[bool] = None,
    tiene_adendas: Optional[bool] = None,
    es_mayor_100m: Optional[bool] = None,
    search: Optional[str] = None,
    order_by: str = "monto_original",
    order_dir: str = "desc",
):
    q = db.query(Contract).options(
        joinedload(Contract.company),
        joinedload(Contract.institution),
    )
    if institution_id:
        q = q.filter(Contract.institution_id == institution_id)
    if company_id:
        q = q.filter(Contract.company_id == company_id)
    if modalidad:
        q = q.filter(Contract.modalidad == modalidad)
    if estado:
        q = q.filter(Contract.estado == estado)
    if monto_min is not None:
        q = q.filter(Contract.monto_original >= monto_min)
    if monto_max is not None:
        q = q.filter(Contract.monto_original <= monto_max)
    if financiado_prestamo is not None:
        q = q.filter(Contract.financiado_prestamo == financiado_prestamo)
    if tiene_adendas is not None:
        q = q.filter(Contract.tiene_adendas == tiene_adendas)
    if es_mayor_100m is not None:
        q = q.filter(Contract.es_mayor_100m == es_mayor_100m)
    if search:
        q = q.filter(or_(
            Contract.descripcion.ilike(f"%{search}%"),
            Contract.objeto.ilike(f"%{search}%"),
            Contract.numero_contrato.ilike(f"%{search}%"),
        ))

    total = q.count()
    col = getattr(Contract, order_by, Contract.monto_original)
    if order_dir == "desc":
        q = q.order_by(desc(col))
    else:
        q = q.order_by(col)

    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize_contract(c) for c in items],
    }


@router.get("/stats")
def contract_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Contract.id)).scalar()
    total_monto = db.query(func.sum(Contract.monto_original)).scalar() or 0
    con_adendas = db.query(func.count(Contract.id)).filter(Contract.tiene_adendas == True).scalar()
    mayores_100m = db.query(func.count(Contract.id)).filter(Contract.es_mayor_100m == True).scalar()
    financiados = db.query(func.count(Contract.id)).filter(Contract.financiado_prestamo == True).scalar()
    por_modalidad = db.query(
        Contract.modalidad, func.count(Contract.id).label("cnt"), func.sum(Contract.monto_original).label("monto")
    ).group_by(Contract.modalidad).all()

    return {
        "total_contratos": total,
        "total_monto_dop": total_monto,
        "contratos_con_adendas": con_adendas,
        "contratos_mayores_100m": mayores_100m,
        "contratos_financiados_prestamo": financiados,
        "por_modalidad": [
            {"modalidad": r.modalidad, "cantidad": r.cnt, "monto": r.monto}
            for r in por_modalidad
        ],
    }


@router.get("/top-100")
def top_100_contracts(
    db: Session = Depends(get_db),
    institution_id: Optional[int] = None,
):
    q = db.query(Contract).options(
        joinedload(Contract.company),
        joinedload(Contract.institution),
    )
    if institution_id:
        q = q.filter(Contract.institution_id == institution_id)
    items = q.order_by(desc(Contract.monto_original)).limit(100).all()
    return [_serialize_contract(c) for c in items]


@router.get("/{contract_id}")
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    c = db.query(Contract).options(
        joinedload(Contract.company),
        joinedload(Contract.institution),
        joinedload(Contract.addenda),
        joinedload(Contract.payments),
        joinedload(Contract.documents),
    ).filter(Contract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "Contrato no encontrado")
    return _serialize_contract(c, full=True)


def _serialize_contract(c: Contract, full: bool = False) -> dict:
    data = {
        "id": c.id,
        "numero_contrato": c.numero_contrato,
        "numero_proceso": c.numero_proceso,
        "descripcion": c.descripcion,
        "objeto": c.objeto,
        "modalidad": c.modalidad,
        "estado": c.estado,
        "monto_original": c.monto_original,
        "monto_actual": c.monto_actual or c.monto_original,
        "monto_pagado": c.monto_pagado,
        "moneda": c.moneda,
        "fecha_firma": c.fecha_firma.isoformat() if c.fecha_firma else None,
        "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
        "fecha_fin_planificada": c.fecha_fin_planificada.isoformat() if c.fecha_fin_planificada else None,
        "oficial_firmante": c.oficial_firmante,
        "tiene_adendas": c.tiene_adendas,
        "num_adendas": c.num_adendas,
        "incremento_porcentual": c.incremento_porcentual,
        "retraso_dias": c.retraso_dias,
        "financiado_prestamo": c.financiado_prestamo,
        "es_mayor_100m": c.es_mayor_100m,
        "fuente": c.fuente,
        "url_fuente": c.url_fuente,
        "raw_data": c.raw_data,
        "institution_id": c.institution_id,
        "company_id": c.company_id,
        "empresa_nombre": c.company.nombre if c.company else None,
        "empresa_rnc": c.company.rnc if c.company else None,
        "institucion_nombre": c.institution.nombre if c.institution else None,
        "institucion_siglas": c.institution.siglas if c.institution else None,
    }
    if full:
        data["adendas"] = [
            {"id": a.id, "numero": a.numero, "descripcion": a.descripcion,
             "monto_adicional": a.monto_adicional, "dias_adicionales": a.dias_adicionales,
             "fecha": a.fecha.isoformat() if a.fecha else None}
            for a in (c.addenda or [])
        ]
        data["pagos"] = [
            {"id": p.id, "monto": p.monto, "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
             "descripcion": p.descripcion}
            for p in (c.payments or [])
        ]
    return data
