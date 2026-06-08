from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.institution import Institution
from ...models.contract import Contract

router = APIRouter(prefix="/institutions", tags=["Instituciones"])


@router.get("/")
def list_institutions(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    tipo: Optional[str] = None,
):
    q = db.query(Institution)
    if search:
        q = q.filter(Institution.nombre.ilike(f"%{search}%"))
    if tipo:
        q = q.filter(Institution.tipo == tipo)
    items = q.order_by(desc(Institution.total_monto_contratos)).all()
    return [_serialize(i) for i in items]


@router.get("/ranking")
def institution_ranking(db: Session = Depends(get_db), limit: int = 30):
    rows = db.query(
        Institution.id, Institution.nombre, Institution.siglas, Institution.tipo,
        func.count(Contract.id).label("num_contratos"),
        func.sum(Contract.monto_original).label("monto_total"),
        func.count(func.distinct(Contract.company_id)).label("num_empresas"),
    ).join(Contract, Contract.institution_id == Institution.id)\
     .group_by(Institution.id, Institution.nombre, Institution.siglas, Institution.tipo)\
     .order_by(desc("monto_total")).limit(limit).all()
    return [
        {"id": r.id, "nombre": r.nombre, "siglas": r.siglas, "tipo": r.tipo,
         "num_contratos": r.num_contratos, "monto_total": r.monto_total,
         "num_empresas": r.num_empresas}
        for r in rows
    ]


@router.get("/{institution_id}")
def get_institution(institution_id: int, db: Session = Depends(get_db)):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    data = _serialize(inst)
    top_empresas = db.query(
        func.sum(Contract.monto_original).label("monto"),
        func.count(Contract.id).label("cnt"),
        Contract.company_id,
    ).filter(Contract.institution_id == institution_id)\
     .group_by(Contract.company_id)\
     .order_by(desc("monto")).limit(10).all()
    data["top_empresas"] = [
        {"company_id": r.company_id, "monto": r.monto, "num_contratos": r.cnt}
        for r in top_empresas
    ]
    return data


def _serialize(i: Institution) -> dict:
    return {
        "id": i.id, "codigo": i.codigo, "nombre": i.nombre, "siglas": i.siglas,
        "tipo": i.tipo, "descripcion": i.descripcion,
        "presupuesto_anual": i.presupuesto_anual,
        "sitio_web": i.sitio_web, "activo": i.activo,
        "total_contratos": i.total_contratos,
        "total_monto_contratos": i.total_monto_contratos,
    }
