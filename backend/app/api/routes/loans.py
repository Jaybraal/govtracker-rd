from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.loan import Loan
from ...models.contract import Contract

router = APIRouter(prefix="/loans", tags=["Préstamos"])


@router.get("/")
def list_loans(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
    acreedor: Optional[str] = None,
    estado: Optional[str] = None,
    search: Optional[str] = None,
):
    q = db.query(Loan)
    if acreedor:
        q = q.filter(Loan.acreedor.ilike(f"%{acreedor}%"))
    if estado:
        q = q.filter(Loan.estado == estado)
    if search:
        q = q.filter(Loan.descripcion.ilike(f"%{search}%") | Loan.objeto.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(desc(Loan.monto_aprobado)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize(l) for l in items],
    }


@router.get("/stats")
def loan_stats(db: Session = Depends(get_db)):
    total_monto = db.query(func.sum(Loan.monto_aprobado)).scalar() or 0
    total_desembolsado = db.query(func.sum(Loan.monto_desembolsado)).scalar() or 0
    por_acreedor = db.query(
        Loan.acreedor,
        func.count(Loan.id).label("cnt"),
        func.sum(Loan.monto_aprobado).label("monto"),
    ).group_by(Loan.acreedor).order_by(desc("monto")).all()
    return {
        "total_aprobado_usd": total_monto,
        "total_desembolsado_usd": total_desembolsado,
        "porcentaje_desembolsado": (total_desembolsado / total_monto * 100) if total_monto else 0,
        "por_acreedor": [
            {"acreedor": r.acreedor, "cantidad": r.cnt, "monto": r.monto}
            for r in por_acreedor
        ],
    }


@router.get("/{loan_id}")
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.query(Loan).options(
        joinedload(Loan.institutions),
        joinedload(Loan.projects),
        joinedload(Loan.contracts),
    ).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(404, "Préstamo no encontrado")
    data = _serialize(loan)
    data["instituciones"] = [{"id": i.id, "nombre": i.nombre} for i in loan.institutions]
    data["proyectos"] = [{"id": p.id, "nombre": p.nombre, "estado": p.estado} for p in loan.projects]
    data["contratos"] = [
        {"id": c.id, "numero": c.numero_contrato, "monto": c.monto_original}
        for c in loan.contracts
    ]
    return data


def _serialize(l: Loan) -> dict:
    return {
        "id": l.id, "codigo": l.codigo, "acreedor": l.acreedor,
        "tipo_acreedor": l.tipo_acreedor, "descripcion": l.descripcion,
        "objeto": l.objeto, "estado": l.estado,
        "monto_aprobado": l.monto_aprobado, "monto_desembolsado": l.monto_desembolsado,
        "moneda": l.moneda, "tasa_interes": l.tasa_interes,
        "plazo_anos": l.plazo_anos, "periodo_gracia_anos": l.periodo_gracia_anos,
        "fecha_aprobacion": l.fecha_aprobacion.isoformat() if l.fecha_aprobacion else None,
        "fecha_vencimiento": l.fecha_vencimiento.isoformat() if l.fecha_vencimiento else None,
        "resolucion_congreso": l.resolucion_congreso,
        "fuente": l.fuente, "url_fuente": l.url_fuente,
    }
