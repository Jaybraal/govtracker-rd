from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.commission import Commission, CommissionMember

router = APIRouter(prefix="/congreso", tags=["Congreso — Comisiones"])

# Cargos que ejercen liderazgo/decisión dentro de una comisión
CARGOS_DIRECTIVOS = ["Presidente/a", "Vice-Presidente/a", "Secretario/a"]


@router.get("/comisiones")
def list_comisiones(
    db: Session = Depends(get_db),
    tipo: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    Comisiones del Congreso Nacional (SIL). Las comisiones permanentes
    estudian, dictaminan y aprueban los proyectos de ley antes del Pleno;
    la "Comisión Coordinadora" cumple el rol de mesa directiva / agenda
    legislativa.
    """
    q = db.query(Commission)
    if tipo:
        q = q.filter(Commission.tipo == tipo)
    if search:
        q = q.filter(Commission.nombre.ilike(f"%{search}%"))
    items = q.order_by(Commission.tipo, Commission.nombre).all()
    return [_serialize_comision(c, db) for c in items]


@router.get("/comisiones/stats")
def comisiones_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Commission.id)).scalar()
    total_miembros = db.query(func.count(CommissionMember.id)).scalar()

    por_tipo = db.query(
        Commission.tipo,
        func.count(Commission.id).label("cnt"),
    ).group_by(Commission.tipo).order_by(desc("cnt")).all()

    return {
        "total_comisiones": total,
        "total_membresias": total_miembros,
        "por_tipo": [{"tipo": r.tipo, "cantidad": r.cnt} for r in por_tipo],
    }


@router.get("/directiva")
def get_directiva(db: Session = Depends(get_db)):
    """
    Mesa Directiva / agenda legislativa — "Comisión Coordinadora" del SIL
    (tipo_id_sil=978). Su Presidente/a es, en la práctica, el/la Presidente/a
    de la Cámara de Diputados.
    """
    c = db.query(Commission).filter(Commission.tipo_id_sil == 978).order_by(desc(Commission.fecha_designacion)).first()
    if not c:
        raise HTTPException(404, "Mesa Directiva / Comisión Coordinadora no encontrada — ejecute el ETL del Congreso")
    return _serialize_comision(c, db, with_miembros=True)


@router.get("/comisiones/{comision_id}")
def get_comision(comision_id: int, db: Session = Depends(get_db)):
    c = db.query(Commission).filter(Commission.id == comision_id).first()
    if not c:
        raise HTTPException(404, "Comisión no encontrada")
    return _serialize_comision(c, db, with_miembros=True)


def _serialize_comision(c: Commission, db: Session, with_miembros: bool = False) -> dict:
    miembros_q = db.query(CommissionMember).filter(CommissionMember.comision_id == c.id)
    total_miembros = miembros_q.count()
    directiva = miembros_q.filter(CommissionMember.cargo.in_(CARGOS_DIRECTIVOS)).all()

    data = {
        "id": c.id,
        "comision_id_sil": c.comision_id_sil,
        "nombre": c.nombre,
        "tipo": c.tipo,
        "estado": c.estado,
        "descripcion": c.descripcion,
        "fecha_designacion": c.fecha_designacion.isoformat() if c.fecha_designacion else None,
        "total_miembros": total_miembros,
        "directiva": [_serialize_miembro(m) for m in directiva],
        "fuente": c.fuente,
        "url_fuente": c.url_fuente,
    }
    if with_miembros:
        data["miembros"] = [_serialize_miembro(m) for m in miembros_q.order_by(CommissionMember.cargo).all()]
    return data


def _serialize_miembro(m: CommissionMember) -> dict:
    return {
        "id": m.id,
        "legislator_id": m.legislator_id,
        "legislador_id_sil": m.legislador_id_sil,
        "nombre_completo": m.nombre_completo,
        "partido_siglas": m.partido_siglas,
        "cargo": m.cargo,
        "estado": m.estado,
    }
