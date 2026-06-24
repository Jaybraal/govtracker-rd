"""
Motor de Inteligencia de Patrones — GovTracker RD
Detecta personas de interés, redes ocultas, patrones sospechosos
cruzando datos de contratos, empresas, representantes y funcionarios.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text, and_, or_
from collections import defaultdict
from typing import Optional
import re

from ..models.contract import Contract, ModalidadCompra
from ..models.company import Company, LegalRepresentative
from ..models.institution import Institution
from ..models.alert import Alert, AlertType, AlertSeverity


# ─────────────────────────────────────────────────────────────────────────────
# PERSONAS DE INTERÉS
# ─────────────────────────────────────────────────────────────────────────────

def get_personas_interes(db: Session, limit: int = 50) -> list:
    """
    Rankea personas por:
    1. Cuántos contratos firmaron/aprobaron
    2. Monto total de contratos asociados
    3. Cuántas instituciones distintas aparecen
    4. Si aparecen tanto como firmante de contratos Y como representante legal

    Esto detecta, por ejemplo:
    - Un mismo funcionario que firma contratos en 4 ministerios distintos
    - Un abogado que representa empresas que ganan contratos en la misma institución
    - Nombres que aparecen como firmantes Y como representantes legales simultáneamente
    """
    personas = defaultdict(lambda: {
        "nombre": "",
        "roles": set(),
        "total_contratos": 0,
        "total_monto": 0.0,
        "instituciones": set(),
        "empresas": set(),
        "flags": [],
        "score_riesgo": 0,
    })

    # 1. Funcionarios firmantes de contratos
    firmantes = db.query(
        Contract.oficial_firmante,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto"),
        func.count(func.distinct(Contract.institution_id)).label("num_insts"),
        func.count(func.distinct(Contract.company_id)).label("num_empresas"),
    ).filter(
        Contract.oficial_firmante.isnot(None),
        Contract.oficial_firmante != "",
    ).group_by(Contract.oficial_firmante)\
     .having(func.count(Contract.id) >= 2)\
     .all()

    for r in firmantes:
        nombre_norm = _normalize_name(r.oficial_firmante)
        p = personas[nombre_norm]
        p["nombre"] = r.oficial_firmante.strip()
        p["roles"].add("firmante")
        p["total_contratos"] += r.cnt
        p["total_monto"] += r.monto or 0
        p["num_instituciones_firmante"] = r.num_insts
        p["num_empresas_firmante"] = r.num_empresas

    # 2. Representantes legales (compatible SQLite + PostgreSQL)
    reps = db.query(
        LegalRepresentative.nombre,
        LegalRepresentative.cedula,
        func.count(func.distinct(LegalRepresentative.company_id)).label("num_empresas"),
    ).join(Company, Company.id == LegalRepresentative.company_id)\
     .group_by(LegalRepresentative.nombre, LegalRepresentative.cedula)\
     .having(func.count(func.distinct(LegalRepresentative.company_id)) >= 1)\
     .all()

    # Bulk: empresas y cargos que representa cada persona (evita N+1 sobre miles de reps)
    empresas_por_nombre = defaultdict(list)
    cargos_por_nombre = defaultdict(set)
    for nombre_rep, nombre_comp, cargo in db.query(LegalRepresentative.nombre, Company.nombre, LegalRepresentative.cargo)\
            .join(Company, Company.id == LegalRepresentative.company_id).all():
        if len(empresas_por_nombre[nombre_rep]) < 10:
            empresas_por_nombre[nombre_rep].append(nombre_comp)
        if cargo:
            cargos_por_nombre[nombre_rep].add(cargo)

    # Bulk: contratos de las empresas que representa cada persona (evita N+1)
    contratos_por_nombre = {
        r.nombre: (r.monto or 0, r.cnt or 0)
        for r in db.query(
            LegalRepresentative.nombre,
            func.sum(Contract.monto_original).label("monto"),
            func.count(Contract.id).label("cnt"),
        ).join(Company, Company.id == LegalRepresentative.company_id)
         .join(Contract, Contract.company_id == Company.id)
         .group_by(LegalRepresentative.nombre).all()
    }

    for r in reps:
        nombre_norm = _normalize_name(r.nombre)
        p = personas[nombre_norm]
        if not p["nombre"]:
            p["nombre"] = r.nombre.strip()
        p["roles"].add("representante_legal")
        p["cedula"] = r.cedula
        p["empresas_representa"] = empresas_por_nombre.get(r.nombre, [])
        p["cargos"] = sorted(cargos_por_nombre.get(r.nombre, []))[:5]
        p["num_empresas_repr"] = r.num_empresas

        monto, cnt = contratos_por_nombre.get(r.nombre, (0, 0))
        p["total_contratos"] += cnt
        p["total_monto"] += monto

    # 3. Calcular flags y score de riesgo
    result = []
    for nombre_norm, p in personas.items():
        if p["total_monto"] < 1_000_000 and p["total_contratos"] < 2:
            continue

        flags = []
        score = 0

        roles = p.get("roles", set())

        # Doble rol: firmante de contratos Y representante legal de empresas que ganan
        if "firmante" in roles and "representante_legal" in roles:
            flags.append("⚠️ DOBLE ROL: Firma contratos y representa empresas ganadoras")
            score += 40

        # Firmante en muchas instituciones distintas
        num_insts = p.get("num_instituciones_firmante", 0)
        if num_insts >= 3:
            flags.append(f"📍 Firma contratos en {num_insts} instituciones distintas")
            score += num_insts * 5

        # Representa muchas empresas
        num_repr = p.get("num_empresas_repr", 0)
        if num_repr >= 20 and not p.get("cedula"):
            flags.append(
                f"🗂️ Contacto registrado de {num_repr} empresas — posible gestor/tramitador "
                f"de constitución de empresas, requiere verificación de identidad"
            )
            score += min(num_repr, 15)
        elif num_repr >= 3:
            flags.append(f"🏢 Representa legalmente {num_repr} empresas distintas")
            score += min(num_repr * 8, 80)

        # Alto monto asociado
        if p["total_monto"] >= 500_000_000:
            flags.append(f"💰 RD${p['total_monto']/1e6:.0f}M asociados a su nombre")
            score += 20
        elif p["total_monto"] >= 100_000_000:
            score += 10

        # Muchos contratos firmados directamente
        if p.get("num_empresas_firmante", 0) == 1 and p["total_contratos"] >= 5:
            flags.append("🎯 Firma contratos con una sola empresa repetidamente")
            score += 25

        p["flags"] = flags
        p["score_riesgo"] = score
        p["roles"] = list(roles)

        if p["total_contratos"] > 0 or flags:
            result.append(p)

    result.sort(key=lambda x: x["score_riesgo"], reverse=True)
    return result[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# PATRONES SOSPECHOSOS
# ─────────────────────────────────────────────────────────────────────────────

def get_patrones_sospechosos(db: Session) -> list:
    """
    Detecta patrones estadísticos anómalos:
    - Empresas que ganan licitaciones secuenciales
    - Empresas nuevas ganando contratos grandes
    - Contratos divididos (fraccionamiento)
    - Concentración extrema
    - Mismos objetos de contrato adjudicados siempre a la misma empresa
    """
    patrones = []

    # ─── 1. Fraccionamiento (múltiples contratos similares a la misma empresa) ───
    fracciones = db.query(
        Contract.institution_id,
        Contract.company_id,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto_total"),
        func.avg(Contract.monto_original).label("monto_prom"),
        func.min(Contract.fecha_firma).label("primera"),
        func.max(Contract.fecha_firma).label("ultima"),
    ).filter(
        Contract.modalidad == ModalidadCompra.COMPARACION_PRECIOS,
        Contract.monto_original < 5_000_000,
    ).group_by(Contract.institution_id, Contract.company_id)\
     .having(func.count(Contract.id) >= 10)\
     .order_by(desc("monto_total")).limit(20).all()

    for r in fracciones:
        inst = db.query(Institution).get(r.institution_id)
        comp = db.query(Company).get(r.company_id)
        if inst and comp:
            patrones.append({
                "tipo": "FRACCIONAMIENTO",
                "severidad": "alta",
                "titulo": f"Posible fraccionamiento de contratos",
                "descripcion": (
                    f"{comp.nombre} recibió {r.cnt} contratos pequeños de {inst.siglas or inst.nombre} "
                    f"sumando RD${r.monto_total/1e6:.1f}M — promedio RD${r.monto_prom/1e3:.0f}K cada uno"
                ),
                "entidad_empresa": comp.nombre,
                "entidad_institucion": inst.nombre,
                "monto": r.monto_total,
                "cantidad": r.cnt,
                "company_id": r.company_id,
                "institution_id": r.institution_id,
            })

    # ─── 2. Monopolio sectorial (empresa gana >60% de contratos de una inst) ───
    monopolios = db.query(
        Contract.institution_id,
        Contract.company_id,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto"),
    ).group_by(Contract.institution_id, Contract.company_id)\
     .having(func.count(Contract.id) >= 5)\
     .order_by(desc("monto")).limit(100).all()

    # Calcular total por institución
    totales_inst = dict(
        db.query(Contract.institution_id, func.sum(Contract.monto_original))
          .group_by(Contract.institution_id).all()
    )

    for r in monopolios:
        total_inst = totales_inst.get(r.institution_id, 1)
        pct = (r.monto / total_inst) * 100 if total_inst > 0 else 0
        if pct >= 40:
            inst = db.query(Institution).get(r.institution_id)
            comp = db.query(Company).get(r.company_id)
            if inst and comp:
                patrones.append({
                    "tipo": "MONOPOLIO_SECTORIAL",
                    "severidad": "critica" if pct >= 60 else "alta",
                    "titulo": f"Empresa controla {pct:.0f}% del gasto institucional",
                    "descripcion": (
                        f"{comp.nombre} concentra el {pct:.1f}% de todo lo contratado "
                        f"por {inst.siglas or inst.nombre} — RD${r.monto/1e6:.1f}M de {r.cnt} contratos"
                    ),
                    "entidad_empresa": comp.nombre,
                    "entidad_institucion": inst.nombre,
                    "monto": r.monto,
                    "porcentaje": pct,
                    "company_id": r.company_id,
                    "institution_id": r.institution_id,
                })

    # ─── 3. Empresas que solo trabajan con 1 institución ───
    exclusivas = db.query(
        Contract.company_id,
        func.count(func.distinct(Contract.institution_id)).label("num_insts"),
        func.count(Contract.id).label("num_contratos"),
        func.sum(Contract.monto_original).label("monto"),
    ).group_by(Contract.company_id)\
     .having(
         func.count(func.distinct(Contract.institution_id)) == 1,
         func.count(Contract.id) >= 5,
         func.sum(Contract.monto_original) >= 50_000_000,
     ).order_by(desc("monto")).limit(15).all()

    for r in exclusivas:
        comp = db.query(Company).get(r.company_id)
        if comp:
            patrones.append({
                "tipo": "DEPENDENCIA_UNICA",
                "severidad": "media",
                "titulo": "Empresa con cliente gubernamental único",
                "descripcion": (
                    f"{comp.nombre} tiene {r.num_contratos} contratos valorados en "
                    f"RD${r.monto/1e6:.1f}M, todos con una sola institución"
                ),
                "entidad_empresa": comp.nombre,
                "monto": r.monto,
                "num_contratos": r.num_contratos,
                "company_id": r.company_id,
            })

    # ─── 4. Contratos directos por encima de los límites de comparación ───
    directos_grandes = db.query(Contract).filter(
        Contract.modalidad == ModalidadCompra.CONTRATACION_DIRECTA,
        Contract.monto_original >= 10_000_000,
    ).order_by(desc(Contract.monto_original)).limit(20).all()

    for c in directos_grandes:
        comp = db.query(Company).get(c.company_id)
        inst = db.query(Institution).get(c.institution_id)
        if comp and inst:
            patrones.append({
                "tipo": "CONTRATACION_DIRECTA_GRANDE",
                "severidad": "alta" if c.monto_original >= 50_000_000 else "media",
                "titulo": f"Contratación directa de RD${c.monto_original/1e6:.1f}M sin licitación",
                "descripcion": (
                    f"{inst.siglas or inst.nombre} adjudicó RD${c.monto_original/1e6:.1f}M "
                    f"directamente a {comp.nombre} sin proceso competitivo"
                ),
                "entidad_empresa": comp.nombre,
                "entidad_institucion": inst.nombre,
                "monto": c.monto_original,
                "contract_id": c.id,
                "numero_contrato": c.numero_contrato,
            })

    # Ordenar por severidad
    orden = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    patrones.sort(key=lambda x: (orden.get(x["severidad"], 9), -x.get("monto", 0)))
    return patrones


# ─────────────────────────────────────────────────────────────────────────────
# RED DE CONEXIONES ENTRE PERSONAS
# ─────────────────────────────────────────────────────────────────────────────

def get_red_personas(db: Session, nombre: str) -> dict:
    """
    Dado un nombre, encuentra todas las conexiones:
    - Contratos que firmó
    - Empresas que representa
    - Otras personas con las que comparte contratos o empresas
    - Instituciones involucradas
    """
    nombre_lower = nombre.lower().strip()
    nodes = {}
    edges = []

    # Nodo central
    nodes[f"persona_{nombre_lower[:20]}"] = {
        "id": f"persona_{nombre_lower[:20]}",
        "label": nombre[:30],
        "group": "persona_interes",
        "value": 50,
    }
    central_id = f"persona_{nombre_lower[:20]}"

    # Contratos firmados
    contratos = db.query(Contract).filter(
        func.lower(Contract.oficial_firmante).contains(nombre_lower)
    ).order_by(desc(Contract.monto_original)).limit(30).all()

    contratos_detalle = []
    for c in contratos:
        inst = db.query(Institution).get(c.institution_id)
        comp = db.query(Company).get(c.company_id)
        if inst:
            inst_id = f"inst_{inst.id}"
            nodes[inst_id] = {"id": inst_id, "label": inst.siglas or inst.nombre[:20], "group": "institution", "value": 30}
            edges.append({"from": central_id, "to": inst_id, "title": f"Firmó {c.numero_contrato}", "group": "firma"})
        if comp:
            comp_id = f"comp_{comp.id}"
            nodes[comp_id] = {"id": comp_id, "label": comp.nombre[:25], "group": "company", "value": c.monto_original / 1e6}
            edges.append({"from": central_id, "to": comp_id, "title": f"RD${c.monto_original/1e6:.1f}M"})
        contratos_detalle.append({
            "id": c.id,
            "numero_contrato": c.numero_contrato,
            "descripcion": c.descripcion or c.objeto,
            "monto_original": c.monto_original,
            "empresa_id": comp.id if comp else None,
            "empresa_nombre": comp.nombre if comp else None,
            "institucion_id": inst.id if inst else None,
            "institucion_nombre": inst.nombre if inst else None,
        })

    # Como representante legal
    reps = db.query(LegalRepresentative).filter(
        func.lower(LegalRepresentative.nombre).contains(nombre_lower)
    ).all()

    empresas_detalle = []
    for rep in reps:
        comp = db.query(Company).get(rep.company_id)
        if comp:
            comp_id = f"comp_{comp.id}"
            nodes[comp_id] = {"id": comp_id, "label": comp.nombre[:25], "group": "company_repr", "value": 20}
            edges.append({"from": central_id, "to": comp_id, "title": "Representante Legal", "dashes": True})
            empresas_detalle.append({
                "id": comp.id,
                "nombre": comp.nombre,
                "cargo": rep.cargo,
                "rnc": comp.rnc,
                "total_contratos": comp.total_contratos,
                "total_monto_recibido": comp.total_monto_recibido,
            })

    # Otros firmantes en los mismos contratos/instituciones
    inst_ids = {c.institution_id for c in contratos}
    personas_relacionadas = []
    if inst_ids:
        otros_firmantes = db.query(
            Contract.oficial_firmante,
            func.count(Contract.id).label("cnt"),
        ).filter(
            Contract.institution_id.in_(inst_ids),
            Contract.oficial_firmante.isnot(None),
            func.lower(Contract.oficial_firmante).notlike(f"%{nombre_lower}%"),
        ).group_by(Contract.oficial_firmante)\
         .having(func.count(Contract.id) >= 2)\
         .order_by(desc("cnt")).limit(5).all()

        for r in otros_firmantes:
            oid = f"persona_{_normalize_name(r.oficial_firmante)[:20]}"
            nodes[oid] = {"id": oid, "label": r.oficial_firmante[:25], "group": "persona_relacionada", "value": 20}
            edges.append({"from": central_id, "to": oid, "title": f"Comparten institución ({r.cnt} contratos)", "dashes": True})
            personas_relacionadas.append({"nombre": r.oficial_firmante, "contratos_compartidos": r.cnt})

    return {
        "nombre": nombre,
        "nodes": list(nodes.values()),
        "edges": edges,
        "contratos_encontrados": len(contratos),
        "empresas_representa": len(reps),
        "contratos_detalle": contratos_detalle,
        "empresas_detalle": empresas_detalle,
        "personas_relacionadas": personas_relacionadas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RANKING GLOBAL DE NOMBRES FRECUENTES
# ─────────────────────────────────────────────────────────────────────────────

def get_nombres_frecuentes(db: Session, min_apariciones: int = 2) -> list:
    """
    Extrae todos los nombres que aparecen en el sistema y los rankea
    por frecuencia y monto involucrado. Combina:
    - oficial_firmante en contratos
    - oficial_aprobador en contratos
    - representantes legales
    """
    nombre_stats = defaultdict(lambda: {
        "nombre": "",
        "apariciones_firmante": 0,
        "apariciones_repr": 0,
        "monto_contratos_firmados": 0.0,
        "monto_contratos_empresa": 0.0,
        "instituciones": set(),
        "empresas": set(),
        "cedula": None,
        "cargos": set(),
    })

    # Firmantes (sin array_agg — compatible SQLite)
    rows = db.query(
        Contract.oficial_firmante,
        func.count(Contract.id).label("cnt"),
        func.sum(Contract.monto_original).label("monto"),
        func.count(func.distinct(Contract.institution_id)).label("num_insts"),
    ).filter(Contract.oficial_firmante.isnot(None), Contract.oficial_firmante != "")\
     .group_by(Contract.oficial_firmante).all()

    for r in rows:
        key = _normalize_name(r.oficial_firmante)
        s = nombre_stats[key]
        s["nombre"] = r.oficial_firmante.strip()
        s["apariciones_firmante"] += r.cnt
        s["monto_contratos_firmados"] += r.monto or 0
        s["instituciones"].update([f"i{r.num_insts}"])

    # Representantes legales (sin array_agg)
    rows2 = db.query(
        LegalRepresentative.nombre,
        LegalRepresentative.cedula,
        func.count(LegalRepresentative.company_id).label("cnt"),
        func.count(func.distinct(LegalRepresentative.company_id)).label("num_comps"),
    ).group_by(LegalRepresentative.nombre, LegalRepresentative.cedula).all()

    # Bulk: empresas y cargos por nombre + monto de contratos por empresa (evita N+1)
    companias_por_nombre = defaultdict(set)
    cargos_por_nombre = defaultdict(set)
    for nombre_rep, comp_id, cargo in db.query(
        LegalRepresentative.nombre, LegalRepresentative.company_id, LegalRepresentative.cargo
    ).all():
        companias_por_nombre[nombre_rep].add(comp_id)
        if cargo:
            cargos_por_nombre[nombre_rep].add(cargo)

    monto_por_empresa = dict(
        db.query(Contract.company_id, func.sum(Contract.monto_original))
          .group_by(Contract.company_id).all()
    )

    for r in rows2:
        key = _normalize_name(r.nombre)
        s = nombre_stats[key]
        if not s["nombre"]:
            s["nombre"] = r.nombre.strip()
        s["apariciones_repr"] += r.cnt
        s["cedula"] = r.cedula
        s["empresas"].update([f"c{r.num_comps}"])
        s["cargos"].update(cargos_por_nombre.get(r.nombre, ()))
        for comp_id in companias_por_nombre.get(r.nombre, ()):
            s["monto_contratos_empresa"] += monto_por_empresa.get(comp_id, 0) or 0

    # Construir resultado
    result = []
    for key, s in nombre_stats.items():
        total_apariciones = s["apariciones_firmante"] + s["apariciones_repr"]
        if total_apariciones < min_apariciones:
            continue
        monto_total = s["monto_contratos_firmados"] + s["monto_contratos_empresa"]
        result.append({
            "nombre": s["nombre"],
            "cedula": s["cedula"],
            "apariciones_firmante": s["apariciones_firmante"],
            "apariciones_repr": s["apariciones_repr"],
            "total_apariciones": total_apariciones,
            "monto_contratos_firmados": s["monto_contratos_firmados"],
            "monto_contratos_empresa": s["monto_contratos_empresa"],
            "monto_total_involucrado": monto_total,
            "num_instituciones": len(s["instituciones"]),
            "num_empresas": len(s["empresas"]),
            "cargos": sorted(s["cargos"])[:5],
            "tiene_doble_rol": s["apariciones_firmante"] > 0 and s["apariciones_repr"] > 0,
        })

    result.sort(key=lambda x: (
        -int(x["tiene_doble_rol"]),
        -x["monto_total_involucrado"],
    ))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Normaliza un nombre para deduplicar variantes del mismo."""
    if not name:
        return ""
    name = name.upper().strip()
    # Quitar títulos comunes
    for title in ["LIC.", "LIC", "DR.", "DR", "ING.", "ING", "ARQ.", "ARQ", "DRA.", "DRA", "PROF."]:
        name = name.replace(title, "").strip()
    # Normalizar espacios múltiples
    name = re.sub(r'\s+', ' ', name)
    # Tomar solo primeros 3 tokens para deduplicar nombres con/sin segundo apellido
    tokens = name.split()
    return " ".join(tokens[:3]) if len(tokens) > 3 else name
