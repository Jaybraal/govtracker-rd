from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.political_party import PoliticalParty, PartyFunding, PartyExpense

router = APIRouter(prefix="/parties", tags=["Partidos Políticos"])


@router.get("/")
def list_parties(db: Session = Depends(get_db)):
    parties = db.query(PoliticalParty).order_by(
        desc(PoliticalParty.votos_ultimas_elecciones)
    ).all()
    return [_serialize(p) for p in parties]


@router.get("/stats")
def party_stats(db: Session = Depends(get_db)):
    total_partidos  = db.query(func.count(PoliticalParty.id)).scalar()
    total_financ    = db.query(func.sum(PartyFunding.monto)).scalar() or 0
    total_gasto     = db.query(func.sum(PartyExpense.monto)).scalar() or 0
    total_senadores = db.query(func.sum(PoliticalParty.senadores)).scalar() or 0
    total_diputados = db.query(func.sum(PoliticalParty.diputados)).scalar() or 0

    financ_por_anio = db.query(
        PartyFunding.anio,
        func.sum(PartyFunding.monto).label("total"),
    ).group_by(PartyFunding.anio).order_by(PartyFunding.anio).all()

    ranking = db.query(
        PoliticalParty.id, PoliticalParty.siglas, PoliticalParty.nombre,
        PoliticalParty.color,
        func.sum(PartyFunding.monto).label("financiamiento"),
        func.sum(PartyExpense.monto).label("gastos"),
    ).outerjoin(PartyFunding, PartyFunding.party_id == PoliticalParty.id)\
     .outerjoin(PartyExpense,  PartyExpense.party_id  == PoliticalParty.id)\
     .group_by(PoliticalParty.id, PoliticalParty.siglas, PoliticalParty.nombre, PoliticalParty.color)\
     .order_by(desc("financiamiento")).all()

    return {
        "total_partidos": total_partidos,
        "total_financiamiento_publico": total_financ,
        "total_gastos_declarados": total_gasto,
        "no_declarado": total_financ - total_gasto,
        "total_senadores": total_senadores,
        "total_diputados": total_diputados,
        "financiamiento_por_anio": [
            {"anio": r.anio, "total": r.total} for r in financ_por_anio
        ],
        "ranking_financiamiento": [
            {"id": r.id, "siglas": r.siglas, "nombre": r.nombre, "color": r.color,
             "financiamiento": r.financiamiento or 0, "gastos": r.gastos or 0,
             "no_declarado": (r.financiamiento or 0) - (r.gastos or 0)}
            for r in ranking
        ],
    }


@router.get("/financiamiento")
def financiamiento_detalle(
    db: Session = Depends(get_db),
    anio: Optional[int] = None,
    party_id: Optional[int] = None,
):
    """Detalle de todos los aportes del Estado a los partidos."""
    q = db.query(PartyFunding).options(joinedload(PartyFunding.party))
    if anio:
        q = q.filter(PartyFunding.anio == anio)
    if party_id:
        q = q.filter(PartyFunding.party_id == party_id)
    rows = q.order_by(desc(PartyFunding.monto)).all()
    return [
        {
            "id": r.id,
            "partido_id": r.party.id if r.party else None,
            "partido": r.party.siglas if r.party else "—",
            "partido_nombre": r.party.nombre if r.party else "—",
            "partido_color": r.party.color if r.party else None,
            "anio": r.anio,
            "trimestre": r.trimestre,
            "monto": r.monto,
            "concepto": r.concepto,
            "fuente_pago": r.fuente_pago,
            "banco_pago": r.banco_pago,
            "resolucion": r.resolucion,
        }
        for r in rows
    ]


@router.get("/gastos")
def gastos_detalle(
    db: Session = Depends(get_db),
    party_id: Optional[int] = None,
    anio: Optional[int] = None,
    categoria: Optional[str] = None,
):
    """Gastos declarados por los partidos ante la JCE."""
    q = db.query(PartyExpense).options(joinedload(PartyExpense.party))
    if party_id:
        q = q.filter(PartyExpense.party_id == party_id)
    if anio:
        q = q.filter(PartyExpense.anio == anio)
    if categoria:
        q = q.filter(PartyExpense.categoria.ilike(f"%{categoria}%"))
    rows = q.order_by(desc(PartyExpense.monto)).all()
    return [
        {
            "partido_id": r.party.id if r.party else None,
            "partido": r.party.siglas if r.party else "—",
            "partido_color": r.party.color if r.party else None,
            "anio": r.anio,
            "categoria": r.categoria,
            "monto": r.monto,
            "descripcion": r.descripcion,
            "proveedor": r.proveedor,
            "proveedor_rnc": r.proveedor_rnc,
        }
        for r in rows
    ]


@router.get("/proveedores")
def proveedores_partidos(db: Session = Depends(get_db)):
    """Empresas que aparecen como proveedores de partidos políticos."""
    rows = db.query(
        PartyExpense.proveedor,
        PartyExpense.proveedor_rnc,
        func.count(PartyExpense.id).label("cnt"),
        func.sum(PartyExpense.monto).label("monto"),
        func.count(func.distinct(PartyExpense.party_id)).label("num_partidos"),
    ).filter(PartyExpense.proveedor.isnot(None))\
     .group_by(PartyExpense.proveedor, PartyExpense.proveedor_rnc)\
     .order_by(desc("monto")).all()

    resultado = []
    for r in rows:
        item = {
            "proveedor": r.proveedor,
            "rnc": r.proveedor_rnc,
            "num_facturas": r.cnt,
            "monto_total": r.monto,
            "num_partidos": r.num_partidos,
        }
        # Cruzar con contratos del Estado
        if r.proveedor_rnc:
            from ...models.company import Company
            comp = db.query(Company).filter(Company.rnc == r.proveedor_rnc).first()
            if comp:
                item["tambien_contratista_estado"] = True
                item["monto_contratos_estado"] = comp.total_monto_recibido
                item["empresa_id"] = comp.id
        resultado.append(item)
    return resultado


@router.get("/{party_id}")
def get_party(party_id: int, db: Session = Depends(get_db)):
    p = db.query(PoliticalParty).options(
        joinedload(PoliticalParty.financiamientos),
        joinedload(PoliticalParty.gastos),
    ).filter(PoliticalParty.id == party_id).first()
    if not p:
        raise HTTPException(404, "Partido no encontrado")
    data = _serialize(p)
    data["financiamientos"] = sorted(
        [{"anio": f.anio, "monto": f.monto, "concepto": f.concepto,
          "banco": f.banco_pago, "resolucion": f.resolucion}
         for f in p.financiamientos],
        key=lambda x: (x["anio"] or 0), reverse=True,
    )
    data["gastos"] = sorted(
        [{"anio": g.anio, "categoria": g.categoria, "monto": g.monto,
          "proveedor": g.proveedor}
         for g in p.gastos],
        key=lambda x: x["monto"] or 0, reverse=True,
    )
    # Calcular transparencia: % del financiamiento que tienen gastos declarados
    total_f = sum(f["monto"] for f in data["financiamientos"])
    total_g = sum(g["monto"] for g in data["gastos"] if g["monto"])
    data["indice_transparencia"] = round((total_g / total_f * 100), 1) if total_f > 0 else 0
    return data


def _serialize(p: PoliticalParty) -> dict:
    return {
        "id": p.id,
        "codigo_jce": p.codigo_jce,
        "rnc": p.rnc,
        "nombre": p.nombre,
        "siglas": p.siglas,
        "color": p.color,
        "estado": p.estado,
        "ideologia": p.ideologia,
        "presidente_partido": p.presidente_partido,
        "candidato_presidencial": p.candidato_presidencial,
        "fecha_fundacion": p.fecha_fundacion.isoformat() if p.fecha_fundacion else None,
        "fundador": p.fundador,
        "sede_principal": p.sede_principal,
        "sitio_web": p.sitio_web,
        "senadores": p.senadores,
        "diputados": p.diputados,
        "sindicos": p.sindicos,
        "regidores": p.regidores,
        "votos_ultimas_elecciones": p.votos_ultimas_elecciones,
        "ano_ultimas_elecciones": p.ano_ultimas_elecciones,
        "total_financiamiento_jce": p.total_financiamiento_jce,
        "financiamiento_anual_promedio": p.financiamiento_anual_promedio,
        "total_contratos_estado": p.total_contratos_estado,
        "total_monto_contratos": p.total_monto_contratos,
    }
