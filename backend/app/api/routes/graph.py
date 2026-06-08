from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
import json
from ...core.database import get_db
from ...models.contract import Contract
from ...models.company import Company, LegalRepresentative
from ...models.institution import Institution
from ...models.loan import Loan

router = APIRouter(prefix="/graph", tags=["Grafo de Relaciones"])


@router.get("/network")
def get_network(
    db: Session = Depends(get_db),
    entity_type: str = Query("company", enum=["company", "institution", "loan", "official"]),
    entity_id: Optional[int] = None,
    depth: int = Query(2, ge=1, le=3),
    min_monto: float = Query(0),
):
    """
    Devuelve nodos y aristas para visualización de red.
    Formato compatible con vis.js / D3 force-graph.
    """
    nodes = {}
    edges = []

    if entity_type == "company" and entity_id:
        _expand_company(db, entity_id, nodes, edges, depth, min_monto)
    elif entity_type == "institution" and entity_id:
        _expand_institution(db, entity_id, nodes, edges, depth, min_monto)
    elif entity_type == "loan" and entity_id:
        _expand_loan(db, entity_id, nodes, edges, depth)
    else:
        _global_network(db, nodes, edges, min_monto)

    return {"nodes": list(nodes.values()), "edges": edges}


def _global_network(db, nodes, edges, min_monto=0):
    """Red global: instituciones + top empresas."""
    # El filtro se aplica sobre la SUMA del par institución-empresa, no por contrato individual
    contratos = db.query(
        Contract.institution_id,
        Contract.company_id,
        func.sum(Contract.monto_original).label("monto"),
        func.count(Contract.id).label("cnt"),
    ).group_by(Contract.institution_id, Contract.company_id)\
     .having(func.sum(Contract.monto_original) >= max(min_monto, 0))\
     .order_by(desc("monto")).limit(200).all()

    inst_ids = {r.institution_id for r in contratos}
    comp_ids = {r.company_id for r in contratos}

    insts = db.query(Institution).filter(Institution.id.in_(inst_ids)).all()
    comps = db.query(Company).filter(Company.id.in_(comp_ids)).all()

    for i in insts:
        nodes[f"inst_{i.id}"] = {
            "id": f"inst_{i.id}", "label": i.siglas or i.nombre[:25],
            "title": i.nombre, "group": "institution",
            "value": i.total_monto_contratos or 1,
        }
    for c in comps:
        nodes[f"comp_{c.id}"] = {
            "id": f"comp_{c.id}", "label": c.nombre[:25],
            "title": c.nombre, "group": "company",
            "value": c.total_monto_recibido or 1,
        }
    for r in contratos:
        edges.append({
            "from": f"inst_{r.institution_id}",
            "to": f"comp_{r.company_id}",
            "value": r.monto,
            "title": f"{r.cnt} contratos — RD${r.monto:,.0f}",
            "label": str(r.cnt),
        })


def _expand_company(db, company_id, nodes, edges, depth, min_monto):
    comp = db.query(Company).get(company_id)
    if not comp:
        return
    nodes[f"comp_{comp.id}"] = {
        "id": f"comp_{comp.id}", "label": comp.nombre[:30],
        "group": "company", "value": comp.total_monto_recibido or 1,
    }
    # Representantes legales
    reps = db.query(LegalRepresentative).filter(
        LegalRepresentative.company_id == company_id
    ).all()
    for rep in reps:
        nodes[f"rep_{rep.id}"] = {
            "id": f"rep_{rep.id}", "label": rep.nombre[:25],
            "group": "representative", "value": 10,
        }
        edges.append({"from": f"comp_{comp.id}", "to": f"rep_{rep.id}", "title": rep.cargo})
        if depth >= 2:
            # Otras empresas del mismo representante
            otras = db.query(LegalRepresentative).filter(
                LegalRepresentative.nombre == rep.nombre,
                LegalRepresentative.company_id != company_id,
            ).all()
            for otra in otras:
                otra_comp = db.query(Company).get(otra.company_id)
                if otra_comp:
                    nodes[f"comp_{otra_comp.id}"] = {
                        "id": f"comp_{otra_comp.id}", "label": otra_comp.nombre[:30],
                        "group": "company_related", "value": otra_comp.total_monto_recibido or 1,
                    }
                    edges.append({
                        "from": f"rep_{rep.id}", "to": f"comp_{otra_comp.id}",
                        "title": "Comparte representante", "dashes": True,
                    })
    # Instituciones con contratos
    rows = db.query(
        Contract.institution_id,
        func.sum(Contract.monto_original).label("monto"),
        func.count(Contract.id).label("cnt"),
    ).filter(Contract.company_id == company_id)\
     .group_by(Contract.institution_id).all()
    for r in rows:
        inst = db.query(Institution).get(r.institution_id)
        if inst:
            nodes[f"inst_{inst.id}"] = {
                "id": f"inst_{inst.id}", "label": inst.siglas or inst.nombre[:25],
                "group": "institution", "value": r.monto or 1,
            }
            edges.append({
                "from": f"comp_{comp.id}", "to": f"inst_{inst.id}",
                "value": r.monto, "label": str(r.cnt),
                "title": f"RD${r.monto:,.0f} en {r.cnt} contratos",
            })


def _expand_institution(db, institution_id, nodes, edges, depth, min_monto):
    inst = db.query(Institution).get(institution_id)
    if not inst:
        return
    nodes[f"inst_{inst.id}"] = {
        "id": f"inst_{inst.id}", "label": inst.siglas or inst.nombre[:25],
        "group": "institution", "value": inst.total_monto_contratos or 1,
    }
    rows = db.query(
        Contract.company_id,
        func.sum(Contract.monto_original).label("monto"),
        func.count(Contract.id).label("cnt"),
    ).filter(
        Contract.institution_id == institution_id,
        Contract.monto_original >= min_monto,
    ).group_by(Contract.company_id).order_by(desc("monto")).limit(30).all()

    for r in rows:
        comp = db.query(Company).get(r.company_id)
        if comp:
            nodes[f"comp_{comp.id}"] = {
                "id": f"comp_{comp.id}", "label": comp.nombre[:30],
                "group": "company", "value": r.monto or 1,
            }
            edges.append({
                "from": f"inst_{inst.id}", "to": f"comp_{comp.id}",
                "value": r.monto, "label": str(r.cnt),
            })


def _expand_loan(db, loan_id, nodes, edges, depth):
    loan = db.query(Loan).get(loan_id)
    if not loan:
        return
    nodes[f"loan_{loan.id}"] = {
        "id": f"loan_{loan.id}",
        "label": f"{loan.acreedor}\n${loan.monto_aprobado:,.0f}M",
        "group": "loan", "value": loan.monto_aprobado or 1,
    }
    for inst in loan.institutions:
        nodes[f"inst_{inst.id}"] = {
            "id": f"inst_{inst.id}", "label": inst.siglas or inst.nombre[:25],
            "group": "institution", "value": inst.total_monto_contratos or 1,
        }
        edges.append({"from": f"loan_{loan.id}", "to": f"inst_{inst.id}"})
    for proj in loan.projects:
        nodes[f"proj_{proj.id}"] = {
            "id": f"proj_{proj.id}", "label": proj.nombre[:30],
            "group": "project", "value": proj.monto_total or 1,
        }
        edges.append({"from": f"loan_{loan.id}", "to": f"proj_{proj.id}"})
