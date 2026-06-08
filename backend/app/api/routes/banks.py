from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from typing import Optional
from ...core.database import get_db
from ...models.bank import Bank, BankType, CompanyBankAccount, InstitutionBankAccount
from ...models.company import Company
from ...models.institution import Institution

router = APIRouter(prefix="/banks", tags=["Bancos"])


@router.get("/")
def list_banks(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    tipo: Optional[str] = None,
    es_estatal: Optional[bool] = None,
    custodia_estado: Optional[bool] = None,
    order_by: str = "activos_totales",
):
    q = db.query(Bank)
    if search:
        q = q.filter(or_(Bank.nombre.ilike(f"%{search}%"), Bank.nombre_corto.ilike(f"%{search}%")))
    if tipo:
        q = q.filter(Bank.tipo == tipo)
    if es_estatal is not None:
        q = q.filter(Bank.es_estatal == es_estatal)
    if custodia_estado is not None:
        q = q.filter(Bank.custodia_fondos_estado == custodia_estado)
    col = getattr(Bank, order_by, Bank.activos_totales)
    return [_serialize(b) for b in q.order_by(desc(col)).all()]


@router.get("/stats")
def bank_stats(db: Session = Depends(get_db)):
    total        = db.query(func.count(Bank.id)).scalar()
    total_activos = db.query(func.sum(Bank.activos_totales)).scalar() or 0
    total_depositos = db.query(func.sum(Bank.depositos_totales)).scalar() or 0
    total_fondos_estado = db.query(func.sum(Bank.monto_fondos_estado)).scalar() or 0
    con_fondos_estado = db.query(func.count(Bank.id)).filter(Bank.custodia_fondos_estado == True).scalar()

    por_tipo = db.query(
        Bank.tipo,
        func.count(Bank.id).label("cnt"),
        func.sum(Bank.activos_totales).label("activos"),
        func.sum(Bank.depositos_totales).label("depositos"),
    ).group_by(Bank.tipo).order_by(desc("activos")).all()

    ranking_fondos_estado = db.query(Bank).filter(
        Bank.custodia_fondos_estado == True
    ).order_by(desc(Bank.monto_fondos_estado)).all()

    return {
        "total_bancos": total,
        "total_activos_sistema": total_activos,
        "total_depositos_sistema": total_depositos,
        "total_fondos_estado_custodiados": total_fondos_estado,
        "bancos_con_fondos_estado": con_fondos_estado,
        "por_tipo": [
            {"tipo": r.tipo, "cantidad": r.cnt, "activos": r.activos, "depositos": r.depositos}
            for r in por_tipo
        ],
        "ranking_fondos_estado": [
            {"id": b.id, "nombre": b.nombre_corto or b.nombre,
             "monto_fondos_estado": b.monto_fondos_estado,
             "num_cuentas": b.num_cuentas_instituciones,
             "es_banco_pagador": b.es_banco_pagador}
            for b in ranking_fondos_estado
        ],
    }


@router.get("/fondos-estado")
def fondos_estado_por_banco(db: Session = Depends(get_db)):
    """Detalla qué institución tiene cuentas en qué banco."""
    rows = db.query(InstitutionBankAccount).options(
        joinedload(InstitutionBankAccount.bank),
    ).order_by(desc(InstitutionBankAccount.monto_depositado)).all()

    resultado = []
    for r in rows:
        inst = db.query(Institution).filter(Institution.id == r.institution_id).first()
        resultado.append({
            "banco": r.bank.nombre_corto if r.bank else "—",
            "banco_tipo": r.bank.tipo if r.bank else None,
            "banco_estatal": r.bank.es_estatal if r.bank else False,
            "institucion_id": r.institution_id,
            "institucion": inst.nombre if inst else "—",
            "institucion_siglas": inst.siglas if inst else "—",
            "descripcion": r.descripcion,
            "monto_depositado": r.monto_depositado,
            "tipo_fondo": r.tipo_fondo,
            "fuente": r.fuente,
        })
    return resultado


@router.get("/empresas-por-banco/{bank_id}")
def empresas_por_banco(bank_id: int, db: Session = Depends(get_db), limit: int = 50):
    """Qué empresas contratistas del Estado tienen cuenta en este banco."""
    banco = db.query(Bank).filter(Bank.id == bank_id).first()
    if not banco:
        raise HTTPException(404, "Banco no encontrado")

    cuentas = db.query(CompanyBankAccount).filter(
        CompanyBankAccount.bank_id == bank_id
    ).limit(limit).all()

    resultado = []
    for cuenta in cuentas:
        comp = db.query(Company).filter(Company.id == cuenta.company_id).first()
        if comp:
            resultado.append({
                "empresa_id": comp.id,
                "empresa": comp.nombre,
                "rnc": comp.rnc,
                "total_contratos": comp.total_contratos,
                "total_monto_estado": comp.total_monto_recibido,
                "tipo_cuenta": cuenta.tipo_cuenta,
                "verificado": cuenta.verificado,
                "fuente": cuenta.fuente,
            })
    resultado.sort(key=lambda x: x["total_monto_estado"] or 0, reverse=True)
    return {"banco": _serialize(banco), "empresas": resultado}


@router.get("/{bank_id}")
def get_bank(bank_id: int, db: Session = Depends(get_db)):
    b = db.query(Bank).filter(Bank.id == bank_id).first()
    if not b:
        raise HTTPException(404, "Banco no encontrado")
    data = _serialize(b)
    # Cuentas de instituciones en este banco
    cuentas_inst = db.query(InstitutionBankAccount).filter(
        InstitutionBankAccount.bank_id == bank_id
    ).order_by(desc(InstitutionBankAccount.monto_depositado)).all()
    data["cuentas_instituciones"] = []
    for c in cuentas_inst:
        inst = db.query(Institution).filter(Institution.id == c.institution_id).first()
        data["cuentas_instituciones"].append({
            "institucion": inst.nombre if inst else "—",
            "siglas": inst.siglas if inst else "—",
            "descripcion": c.descripcion,
            "monto_depositado": c.monto_depositado,
            "tipo_fondo": c.tipo_fondo,
        })
    return data


def _serialize(b: Bank) -> dict:
    return {
        "id": b.id,
        "codigo_sib": b.codigo_sib,
        "rnc": b.rnc,
        "nombre": b.nombre,
        "nombre_corto": b.nombre_corto,
        "tipo": b.tipo,
        "es_estatal": b.es_estatal,
        "pais_origen": b.pais_origen,
        "ano_fundacion": b.ano_fundacion,
        "sitio_web": b.sitio_web,
        "num_sucursales": b.num_sucursales,
        "num_empleados": b.num_empleados,
        "activos_totales": b.activos_totales,
        "pasivos_totales": b.pasivos_totales,
        "patrimonio": b.patrimonio,
        "cartera_creditos": b.cartera_creditos,
        "depositos_totales": b.depositos_totales,
        "utilidad_neta": b.utilidad_neta,
        "indice_solvencia": b.indice_solvencia,
        "mora_porcentaje": b.mora_porcentaje,
        "roa": b.roa,
        "roe": b.roe,
        "custodia_fondos_estado": b.custodia_fondos_estado,
        "monto_fondos_estado": b.monto_fondos_estado,
        "num_cuentas_instituciones": b.num_cuentas_instituciones,
        "es_banco_pagador": b.es_banco_pagador,
        "anio_balance": b.anio_balance,
    }
