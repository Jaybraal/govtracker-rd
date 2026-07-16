from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.institution import Institution
from ...models.contract import Contract
from ...models.alert import Alert, AlertType

router = APIRouter(prefix="/institutions", tags=["Instituciones"])

_SEVERITY_WEIGHT = {"baja": 1, "media": 2, "alta": 4, "critica": 8}


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


@router.get("/ranking-riesgo")
def institution_risk_ranking(db: Session = Depends(get_db), limit: int = 30):
    """
    Rankea instituciones por señales de alerta (no por monto gastado, que ya
    cubre /ranking) — responde directamente "dónde está el lío", cruzando los
    3 tipos de alerta que se pueden atribuir a una institución:

      - tipo "contrato" (CONTRATO_GRANDE, INCREMENTO_PRECIO, MUCHAS_ADENDAS,
        ANOMALIA_MONTO, PROVEEDOR_INHABILITADO): join directo Alert→Contract.
      - EMPRESA_CONCENTRADA: el entidad_id es un id sintético
        company_id*100000+institution_id (ver services/alert_scanner.py) —
        se decodifica directo, sin join.
      - EMPRESA_CAUTIVA: entidad_id es el Company.id real; se atribuye a la
        institución donde esa empresa concentra más monto.

    POSIBLE_CONFLICTO (legislador) no se atribuye a una sola institución — el
    legislador puede compartir nombre con representante de empresas que
    contratan con varias instituciones a la vez — se deja fuera de este ranking.
    """
    contadores: dict[int, dict] = {}

    def _acc(institution_id, severidad):
        if not institution_id:
            return
        sev = severidad.value if hasattr(severidad, "value") else severidad
        c = contadores.setdefault(institution_id, {"alertas": 0, "score": 0})
        c["alertas"] += 1
        c["score"] += _SEVERITY_WEIGHT.get(sev, 1)

    # 1. Alertas tipo "contrato"
    for severidad, institution_id in db.query(Alert.severidad, Contract.institution_id).join(
        Contract, Contract.id == Alert.entidad_id
    ).filter(Alert.entidad_tipo == "contrato", Alert.descartada == False).all():
        _acc(institution_id, severidad)

    # 2. EMPRESA_CONCENTRADA — decodificar id sintético
    for severidad, entidad_id in db.query(Alert.severidad, Alert.entidad_id).filter(
        Alert.tipo == AlertType.EMPRESA_CONCENTRADA, Alert.descartada == False
    ).all():
        _acc(entidad_id % 100000, severidad)

    # 3. EMPRESA_CAUTIVA — institución donde la empresa concentra más monto
    cautivas = db.query(Alert.severidad, Alert.entidad_id).filter(
        Alert.tipo == AlertType.EMPRESA_CAUTIVA, Alert.descartada == False
    ).all()
    if cautivas:
        company_ids = [r.entidad_id for r in cautivas]
        top_inst_por_empresa: dict[int, tuple] = {}
        for company_id, institution_id, monto in db.query(
            Contract.company_id, Contract.institution_id,
            func.sum(Contract.monto_original).label("monto"),
        ).filter(Contract.company_id.in_(company_ids))\
         .group_by(Contract.company_id, Contract.institution_id).all():
            cur = top_inst_por_empresa.get(company_id)
            if cur is None or (monto or 0) > cur[1]:
                top_inst_por_empresa[company_id] = (institution_id, monto or 0)
        for severidad, entidad_id in cautivas:
            top = top_inst_por_empresa.get(entidad_id)
            if top:
                _acc(top[0], severidad)

    if not contadores:
        return []

    insts = {i.id: i for i in db.query(Institution).filter(Institution.id.in_(contadores.keys())).all()}
    resultado = []
    for institution_id, c in contadores.items():
        inst = insts.get(institution_id)
        if not inst:
            continue
        resultado.append({
            "institution_id": institution_id, "nombre": inst.nombre, "siglas": inst.siglas,
            "num_alertas": c["alertas"], "score_riesgo": c["score"],
            "total_contratos": inst.total_contratos, "total_monto_contratos": inst.total_monto_contratos,
        })
    resultado.sort(key=lambda r: r["score_riesgo"], reverse=True)
    return resultado[:limit]


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
