from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from typing import Optional
from ...core.database import get_db
from ...models.company import Company, LegalRepresentative, SupplierDisqualification
from ...models.contract import Contract

router = APIRouter(prefix="/companies", tags=["Empresas"])


@router.get("/")
def list_companies(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
    search: Optional[str] = None,
    rnc: Optional[str] = None,
    sector: Optional[str] = None,
    min_contratos: Optional[int] = None,
    min_monto: Optional[float] = None,
    order_by: str = "total_monto_recibido",
    order_dir: str = "desc",
):
    q = db.query(Company)
    if search:
        q = q.filter(or_(
            Company.nombre.ilike(f"%{search}%"),
            Company.nombre_comercial.ilike(f"%{search}%"),
            Company.rnc.ilike(f"%{search}%"),
        ))
    if rnc:
        q = q.filter(Company.rnc == rnc)
    if sector:
        q = q.filter(Company.sector.ilike(f"%{sector}%"))
    if min_contratos:
        q = q.filter(Company.total_contratos >= min_contratos)
    if min_monto:
        q = q.filter(Company.total_monto_recibido >= min_monto)

    total = q.count()
    col = getattr(Company, order_by, Company.total_monto_recibido)
    q = q.order_by(desc(col) if order_dir == "desc" else col)
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize_company(c) for c in items],
    }


@router.get("/ranking")
def company_ranking(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    institution_id: Optional[int] = None,
):
    """Top empresas por monto recibido del Estado."""
    q = db.query(
        Company.id, Company.nombre, Company.rnc, Company.sector,
        func.count(Contract.id).label("num_contratos"),
        func.sum(Contract.monto_original).label("monto_total"),
        func.count(func.distinct(Contract.institution_id)).label("num_instituciones"),
    ).join(Contract, Contract.company_id == Company.id)
    if institution_id:
        q = q.filter(Contract.institution_id == institution_id)
    rows = q.group_by(Company.id, Company.nombre, Company.rnc, Company.sector)\
            .order_by(desc("monto_total")).limit(limit).all()
    return [
        {"id": r.id, "nombre": r.nombre, "rnc": r.rnc, "sector": r.sector,
         "num_contratos": r.num_contratos, "monto_total": r.monto_total,
         "num_instituciones": r.num_instituciones}
        for r in rows
    ]


@router.get("/shared-representatives")
def companies_with_shared_representatives(db: Session = Depends(get_db)):
    """Detecta representantes legales que aparecen en múltiples empresas."""
    # Usamos Python para agrupar (compatible SQLite + PostgreSQL)
    rows = db.query(
        LegalRepresentative.nombre,
        LegalRepresentative.cedula,
        func.count(LegalRepresentative.company_id).label("num_empresas"),
    ).join(Company, Company.id == LegalRepresentative.company_id)\
     .group_by(LegalRepresentative.nombre, LegalRepresentative.cedula)\
     .having(func.count(LegalRepresentative.company_id) > 1)\
     .order_by(desc("num_empresas")).all()

    result = []
    for r in rows:
        empresas = db.query(Company.nombre).join(
            LegalRepresentative, LegalRepresentative.company_id == Company.id
        ).filter(LegalRepresentative.nombre == r.nombre).all()
        result.append({
            "nombre": r.nombre, "cedula": r.cedula,
            "num_empresas": r.num_empresas,
            "empresas": [e[0] for e in empresas],
        })
    return result


@router.get("/inhabilitados")
def proveedores_inhabilitados_con_contratos(db: Session = Depends(get_db), limit: int = Query(100, le=500)):
    """Empresas del registro oficial DGCP/SECP de Proveedores Inhabilitados que
    firmaron contratos con el Estado EN O DESPUÉS de la fecha de su sanción —
    es decir, contrataron pese a estar ya sancionadas por el propio órgano
    regulador (a menudo de forma permanente, por documentos falsos o
    incumplimiento contractual). Cada caso queda documentado con el número de
    resolución/oficio oficial, motivo, fecha de sanción y los contratos
    posteriores con su monto y estado actual."""
    rows = db.query(Contract, SupplierDisqualification, Company).join(
        SupplierDisqualification, SupplierDisqualification.company_id == Contract.company_id
    ).join(Company, Company.id == Contract.company_id).filter(
        Contract.fecha_firma.isnot(None),
        SupplierDisqualification.fecha_inhabilitacion.isnot(None),
        Contract.fecha_firma >= SupplierDisqualification.fecha_inhabilitacion,
    ).order_by(desc(Contract.monto_original)).all()

    # Una empresa puede tener varios eventos de sanción que un mismo contrato
    # incumple a la vez — cada contrato se documenta UNA sola vez, bajo el
    # evento de sanción MÁS ANTIGUO que ya incumplía (evita doble conteo y es
    # consistente con la alerta generada para ese contrato)
    earliest_per_contract: dict[int, tuple] = {}
    for c, d, comp in rows:
        cur = earliest_per_contract.get(c.id)
        if cur is None or d.fecha_inhabilitacion < cur[1].fecha_inhabilitacion:
            earliest_per_contract[c.id] = (c, d, comp)

    by_company: dict[int, dict] = {}
    for c, d, comp in earliest_per_contract.values():
        entry = by_company.setdefault(comp.id, {
            "company_id": comp.id, "rpe": comp.rpe, "nombre": comp.nombre,
            "total_contratos": comp.total_contratos, "total_monto_recibido": comp.total_monto_recibido,
            "casos": {}, "fuente": d.fuente, "url_fuente": d.url_fuente,
        })
        caso_key = (d.motivo, d.fecha_inhabilitacion)
        caso = entry["casos"].setdefault(caso_key, {
            "motivo": d.motivo,
            "oficio": d.oficio_inhabilitacion,
            "fecha_inhabilitacion": d.fecha_inhabilitacion.isoformat(),
            "fecha_habilitacion": d.fecha_habilitacion.isoformat() if d.fecha_habilitacion else None,
            "url_certificacion": d.url_certificacion,
            "permanente": "permanentemente" in (d.motivo or "").lower(),
            "contratos": [],
        })
        caso["contratos"].append({
            "id": c.id, "numero": c.numero_contrato,
            "fecha_firma": c.fecha_firma.isoformat(),
            "monto": c.monto_original,
            "estado": c.estado.value if c.estado else None,
            "objeto": c.objeto or c.descripcion,
        })

    items = []
    for entry in by_company.values():
        casos = sorted(entry.pop("casos").values(), key=lambda k: k["fecha_inhabilitacion"])
        monto = sum(ct["monto"] or 0 for caso in casos for ct in caso["contratos"])
        n = sum(len(caso["contratos"]) for caso in casos)
        items.append({**entry, "casos": casos, "monto_contratos_posteriores": monto, "num_contratos_posteriores": n})

    items.sort(key=lambda r: -r["monto_contratos_posteriores"])
    return {
        "resumen": {
            "empresas": len(items),
            "contratos_posteriores_a_inhabilitacion": sum(i["num_contratos_posteriores"] for i in items),
            "monto_total_contratos_posteriores": sum(i["monto_contratos_posteriores"] for i in items),
            "fuente": "DGCP — Registro de Proveedores del Estado Inhabilitados (SECP), cruzado por RPE contra adjudicaciones DGCP",
        },
        "items": items[:limit],
    }


@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).options(
        joinedload(Company.legal_representatives),
    ).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404, "Empresa no encontrada")
    data = _serialize_company(c)
    data["representantes"] = [
        {"id": r.id, "nombre": r.nombre, "cedula": r.cedula, "cargo": r.cargo,
         "telefono": r.telefono, "email": r.email}
        for r in c.legal_representatives
    ]
    # Contratos recientes
    contratos = db.query(Contract).filter(Contract.company_id == company_id)\
                  .order_by(desc(Contract.monto_original)).limit(20).all()
    data["contratos_recientes"] = [
        {"id": ct.id, "numero": ct.numero_contrato, "monto": ct.monto_original,
         "institucion_id": ct.institution_id, "descripcion": ct.descripcion}
        for ct in contratos
    ]
    return data


def _serialize_company(c: Company) -> dict:
    return {
        "id": c.id, "rnc": c.rnc, "nombre": c.nombre,
        "nombre_comercial": c.nombre_comercial, "tipo_empresa": c.tipo_empresa,
        "sector": c.sector, "telefono": c.telefono, "email": c.email,
        "direccion": c.direccion, "provincia": c.provincia,
        "total_contratos": c.total_contratos,
        "total_monto_recibido": c.total_monto_recibido,
        "total_instituciones": c.total_instituciones,
        "indice_concentracion": c.indice_concentracion,
        "primer_contrato": c.primer_contrato.isoformat() if c.primer_contrato else None,
        "ultimo_contrato": c.ultimo_contrato.isoformat() if c.ultimo_contrato else None,
    }
