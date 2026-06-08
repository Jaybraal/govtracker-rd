from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import Optional
from ...core.database import get_db
from ...models.cooperative import Cooperative, CoopType, CoopStatus

router = APIRouter(prefix="/cooperatives", tags=["Cooperativas"])


@router.get("/")
def list_cooperatives(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(100, le=500),
    search: Optional[str] = None,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    provincia: Optional[str] = None,
    con_contratos: Optional[bool] = None,
    order_by: str = "activos_totales",
    order_dir: str = "desc",
):
    q = db.query(Cooperative)
    if search:
        q = q.filter(or_(
            Cooperative.nombre.ilike(f"%{search}%"),
            Cooperative.siglas.ilike(f"%{search}%"),
            Cooperative.rnc.ilike(f"%{search}%"),
        ))
    if tipo:
        q = q.filter(Cooperative.tipo == tipo)
    if estado:
        q = q.filter(Cooperative.estado == estado)
    if provincia:
        q = q.filter(Cooperative.provincia.ilike(f"%{provincia}%"))
    if con_contratos is True:
        q = q.filter(Cooperative.total_contratos_estado > 0)
    if con_contratos is False:
        q = q.filter(Cooperative.total_contratos_estado == 0)

    total = q.count()
    col = getattr(Cooperative, order_by, Cooperative.activos_totales)
    q = q.order_by(desc(col) if order_dir == "desc" else col)
    items = q.offset((page - 1) * size).limit(size).all()

    return {
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize(c) for c in items],
    }


@router.get("/stats")
def cooperative_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Cooperative.id)).scalar()
    total_socios = db.query(func.sum(Cooperative.num_socios)).scalar() or 0
    total_activos = db.query(func.sum(Cooperative.activos_totales)).scalar() or 0
    con_contratos = db.query(func.count(Cooperative.id)).filter(
        Cooperative.total_contratos_estado > 0
    ).scalar()

    por_tipo = db.query(
        Cooperative.tipo,
        func.count(Cooperative.id).label("cnt"),
        func.sum(Cooperative.activos_totales).label("activos"),
        func.sum(Cooperative.num_socios).label("socios"),
    ).group_by(Cooperative.tipo).order_by(desc("activos")).all()

    por_provincia = db.query(
        Cooperative.provincia,
        func.count(Cooperative.id).label("cnt"),
        func.sum(Cooperative.activos_totales).label("activos"),
    ).filter(Cooperative.provincia.isnot(None))\
     .group_by(Cooperative.provincia).order_by(desc("cnt")).all()

    return {
        "total_cooperativas": total,
        "total_socios": total_socios,
        "total_activos_dop": total_activos,
        "con_contratos_estado": con_contratos,
        "por_tipo": [
            {"tipo": r.tipo, "cantidad": r.cnt, "activos": r.activos, "socios": r.socios}
            for r in por_tipo
        ],
        "por_provincia": [
            {"provincia": r.provincia, "cantidad": r.cnt, "activos": r.activos}
            for r in por_provincia
        ],
    }


@router.get("/con-contratos-estado")
def cooperatives_with_contracts(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    """Cooperativas que han recibido dinero del Estado dominicano."""
    items = db.query(Cooperative).filter(
        Cooperative.total_contratos_estado > 0
    ).order_by(desc(Cooperative.total_monto_contratos)).limit(limit).all()
    return [_serialize(c) for c in items]


@router.get("/{coop_id}")
def get_cooperative(coop_id: int, db: Session = Depends(get_db)):
    c = db.query(Cooperative).filter(Cooperative.id == coop_id).first()
    if not c:
        raise HTTPException(404, "Cooperativa no encontrada")
    data = _serialize(c)

    # Si tiene RNC, buscar empresa y traer contratos
    if c.rnc:
        from ...models.company import Company
        from ...models.contract import Contract
        comp = db.query(Company).filter(Company.rnc == c.rnc).first()
        if comp:
            contratos = db.query(Contract).filter(Contract.company_id == comp.id)\
                          .order_by(desc(Contract.monto_original)).limit(20).all()
            data["contratos_estado"] = [
                {"id": ct.id, "numero": ct.numero_contrato, "monto": ct.monto_original,
                 "institucion_id": ct.institution_id, "descripcion": ct.descripcion}
                for ct in contratos
            ]
    return data


def _serialize(c: Cooperative) -> dict:
    return {
        "id": c.id,
        "numero_registro": c.numero_registro,
        "rnc": c.rnc,
        "nombre": c.nombre,
        "siglas": c.siglas,
        "tipo": c.tipo,
        "estado": c.estado,
        "provincia": c.provincia,
        "municipio": c.municipio,
        "telefono": c.telefono,
        "email": c.email,
        "gerente_general": c.gerente_general,
        "presidente_consejo": c.presidente_consejo,
        "num_socios": c.num_socios,
        "activos_totales": c.activos_totales,
        "patrimonio": c.patrimonio,
        "capital_social": c.capital_social,
        "cartera_creditos": c.cartera_creditos,
        "depositos": c.depositos,
        "ingresos": c.ingresos,
        "excedentes": c.excedentes,
        "anio_balance": c.anio_balance,
        "fecha_constitucion": c.fecha_constitucion.isoformat() if c.fecha_constitucion else None,
        "total_contratos_estado": c.total_contratos_estado,
        "total_monto_contratos": c.total_monto_contratos,
        "recibe_subsidio_estado": c.recibe_subsidio_estado,
        "fuente": c.fuente,
        "url_fuente": c.url_fuente,
    }
