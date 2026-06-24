from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import Optional
from ...core.database import get_db
from ...models.legislator import Legislator, LegislatorChamber
from ...models.commission import CommissionMember, Commission

router = APIRouter(prefix="/legislators", tags=["Legisladores"])


@router.get("/")
def list_legislators(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(100, le=500),
    search: Optional[str] = None,
    camara: Optional[str] = None,
    partido_siglas: Optional[str] = None,
    provincia: Optional[str] = None,
    con_contratos: Optional[bool] = None,
    order_by: str = "nombre_completo",
    order_dir: str = "asc",
):
    q = db.query(Legislator)
    if search:
        q = q.filter(Legislator.nombre_completo.ilike(f"%{search}%"))
    if camara:
        q = q.filter(Legislator.camara == camara)
    if partido_siglas:
        q = q.filter(Legislator.partido_siglas == partido_siglas)
    if provincia:
        q = q.filter(Legislator.provincia.ilike(f"%{provincia}%"))
    if con_contratos is True:
        q = q.filter(Legislator.total_contratos_relacionados > 0)
    if con_contratos is False:
        q = q.filter(Legislator.total_contratos_relacionados == 0)

    total = q.count()
    col = getattr(Legislator, order_by, Legislator.nombre_completo)
    q = q.order_by(desc(col) if order_dir == "desc" else col)
    items = q.offset((page - 1) * size).limit(size).all()

    return {
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize(l) for l in items],
    }


@router.get("/stats")
def legislator_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Legislator.id)).scalar()
    con_contratos = db.query(func.count(Legislator.id)).filter(
        Legislator.total_contratos_relacionados > 0
    ).scalar()

    por_camara = db.query(
        Legislator.camara,
        func.count(Legislator.id).label("cnt"),
    ).group_by(Legislator.camara).all()

    por_partido = db.query(
        Legislator.partido_siglas,
        Legislator.camara,
        func.count(Legislator.id).label("cnt"),
    ).filter(Legislator.partido_siglas.isnot(None))\
     .group_by(Legislator.partido_siglas, Legislator.camara)\
     .order_by(desc("cnt")).all()

    por_provincia = db.query(
        Legislator.provincia,
        func.count(Legislator.id).label("cnt"),
    ).filter(Legislator.provincia.isnot(None))\
     .group_by(Legislator.provincia).order_by(desc("cnt")).all()

    return {
        "total_legisladores": total,
        "con_contratos_relacionados": con_contratos,
        "por_camara": [
            {"camara": r.camara, "cantidad": r.cnt} for r in por_camara
        ],
        "por_partido": [
            {"partido_siglas": r.partido_siglas, "camara": r.camara, "cantidad": r.cnt}
            for r in por_partido
        ],
        "por_provincia": [
            {"provincia": r.provincia, "cantidad": r.cnt} for r in por_provincia
        ],
    }


@router.get("/con-contratos-relacionados")
def legislators_with_contracts(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    """Legisladores cuyo nombre coincide con un representante legal de una empresa contratista del Estado."""
    items = db.query(Legislator).filter(
        Legislator.total_contratos_relacionados > 0
    ).order_by(desc(Legislator.total_monto_relacionado)).limit(limit).all()
    return [_serialize(l) for l in items]


@router.get("/{legislator_id}")
def get_legislator(legislator_id: int, db: Session = Depends(get_db)):
    l = db.query(Legislator).filter(Legislator.id == legislator_id).first()
    if not l:
        raise HTTPException(404, "Legislador no encontrado")
    data = _serialize(l)

    membresias = db.query(CommissionMember, Commission).join(
        Commission, CommissionMember.comision_id == Commission.id
    ).filter(CommissionMember.legislator_id == l.id).all()
    if membresias:
        data["comisiones"] = [
            {
                "comision_id": com.id,
                "nombre": com.nombre,
                "tipo": com.tipo,
                "cargo": mem.cargo,
            }
            for mem, com in membresias
        ]

    if l.total_contratos_relacionados and l.total_contratos_relacionados > 0:
        from ...models.company import LegalRepresentative
        from ...models.contract import Contract
        reps = db.query(LegalRepresentative).filter(
            func.upper(LegalRepresentative.nombre) == l.nombre_completo.upper()
        ).all()
        company_ids = {r.company_id for r in reps}
        if company_ids:
            contratos = db.query(Contract).filter(Contract.company_id.in_(company_ids))\
                          .order_by(desc(Contract.monto_original)).limit(20).all()
            data["contratos_relacionados"] = [
                {"id": ct.id, "numero": ct.numero_contrato, "monto": ct.monto_original,
                 "institucion_id": ct.institution_id, "descripcion": ct.descripcion}
                for ct in contratos
            ]
    return data


def _serialize(l: Legislator) -> dict:
    return {
        "id": l.id,
        "legislador_id_sil": l.legislador_id_sil,
        "nombre_completo": l.nombre_completo,
        "camara": l.camara,
        "funcion": l.funcion,
        "partido_siglas": l.partido_siglas,
        "partido_nombre": l.partido_nombre,
        "provincia": l.provincia,
        "circunscripcion": l.circunscripcion,
        "total_contratos_relacionados": l.total_contratos_relacionados,
        "total_monto_relacionado": l.total_monto_relacionado,
        "fuente": l.fuente,
        "url_fuente": l.url_fuente,
    }
