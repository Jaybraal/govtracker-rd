#!/usr/bin/env python3
"""
Seed de datos demo para GovTracker RD.
Genera datos realistas para demostración sin necesidad de conectar APIs.
Ejecutar: python scripts/seed_demo.py
"""
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import SessionLocal, engine, Base
from app.models import *

Base.metadata.create_all(bind=engine)

db = SessionLocal()

INSTITUCIONES = [
    ("INAPA", "Instituto Nacional de Aguas Potables y Alcantarillados", "empresa_publica"),
    ("MOPC", "Ministerio de Obras Públicas y Comunicaciones", "ministerio"),
    ("MINERD", "Ministerio de Educación", "ministerio"),
    ("MSP", "Ministerio de Salud Pública", "ministerio"),
    ("MH", "Ministerio de Hacienda", "ministerio"),
    ("INTRANT", "Instituto Nacional de Tránsito y Transporte Terrestre", "organismo_autonomo"),
    ("EGEHID", "Empresa de Generación Hidroeléctrica Dominicana", "empresa_publica"),
    ("EDEESTE", "Empresa Distribuidora de Electricidad del Este", "empresa_publica"),
    ("MITUR", "Ministerio de Turismo", "ministerio"),
    ("MEM", "Ministerio de Energía y Minas", "ministerio"),
]

EMPRESAS = [
    ("101234567", "CONSTRUCTORA DEL CARIBE, S.R.L.", "Construcción"),
    ("102345678", "TECNOSERVICIOS RD, S.A.", "Tecnología"),
    ("103456789", "GRUPO EMPRESARIAL OZAMA, C. por A.", "Construcción"),
    ("104567890", "SOLUCIONES INTEGRALES DEL ESTE, S.R.L.", "Consultoría"),
    ("105678901", "IMPORTADORA Y DISTRIBUIDORA NACIONAL, S.A.", "Comercio"),
    ("106789012", "INGENIERÍA Y ARQUITECTURA DOMINICANA, S.R.L.", "Ingeniería"),
    ("107890123", "SISTEMAS Y REDES CARIBEÑAS, S.A.", "Tecnología"),
    ("108901234", "CONSTRUCTORA QUISQUEYA 2000, S.R.L.", "Construcción"),
    ("109012345", "FARMACÉUTICA DEL CARIBE, S.A.", "Salud"),
    ("110123456", "MANTENIMIENTO Y SERVICIOS GENERALES, S.R.L.", "Servicios"),
    ("111234567", "TECNOLOGÍA Y COMUNICACIONES DEL ESTE, S.A.", "Tecnología"),
    ("112345678", "INFRAESTRUCTURA VIAL DOMINICANA, C. por A.", "Construcción"),
    ("113456789", "LABORATORIOS NACIONALES UNIDOS, S.R.L.", "Salud"),
    ("114567890", "CONSULTORES FINANCIEROS DEL CARIBE, S.A.", "Finanzas"),
    ("115678901", "EQUIPOS Y MATERIALES RD, S.R.L.", "Suministros"),
]

MODALIDADES = [
    "licitacion_publica", "licitacion_publica", "licitacion_publica",
    "comparacion_precios", "comparacion_precios",
    "contratacion_directa",
    "subasta_inversa",
    "licitacion_restringida",
]

def rand_monto(base=1_000_000, top=500_000_000):
    return round(random.uniform(base, top) / 1000) * 1000

def rand_date(years_back=4):
    days = random.randint(0, 365 * years_back)
    return datetime.now() - timedelta(days=days)

print("🌱 Sembrando datos demo...")

# Instituciones
institutions = []
for siglas, nombre, tipo in INSTITUCIONES:
    inst = Institution(siglas=siglas, nombre=nombre, tipo=tipo, codigo=f"GOB-{siglas}")
    db.add(inst)
    institutions.append(inst)
db.flush()
print(f"  ✅ {len(institutions)} instituciones creadas")

# Empresas
companies = []
for rnc, nombre, sector in EMPRESAS:
    comp = Company(rnc=rnc, nombre=nombre, sector=sector)
    db.add(comp)
    companies.append(comp)
    # Rep legal
    rep = LegalRepresentative(
        company=comp,
        nombre=random.choice(["JUAN PÉREZ MARTÍNEZ", "MARÍA RODRÍGUEZ", "CARLOS GÓMEZ DÍAZ", "ANA JIMÉNEZ"]),
        cargo="Representante Legal",
    )
    db.add(rep)
db.flush()
print(f"  ✅ {len(companies)} empresas creadas")

# Préstamos
loans_data = [
    ("BID", 200_000_000, "Programa de Agua y Saneamiento", "activo"),
    ("Banco Mundial", 120_000_000, "Programa Educación Básica", "en_desembolso"),
    ("CAF", 300_000_000, "Programa Infraestructura Vial", "en_desembolso"),
    ("China Eximbank", 1_900_000_000, "Planta Termoeléctrica Punta Catalina", "activo"),
    ("BID", 80_000_000, "Modernización del Estado", "activo"),
]
loans = []
for i, (acreedor, monto, desc, estado) in enumerate(loans_data):
    loan = Loan(
        codigo=f"LOAN-{i+1:04d}",
        acreedor=acreedor,
        tipo_acreedor="multilateral" if acreedor != "China Eximbank" else "bilateral",
        descripcion=desc, objeto=desc,
        estado=estado,
        monto_aprobado=monto,
        monto_desembolsado=monto * random.uniform(0.3, 0.95),
        moneda="USD",
        tasa_interes=round(random.uniform(1.5, 5.0), 2),
        plazo_anos=random.choice([15, 20, 25, 30]),
        fecha_aprobacion=rand_date(5),
    )
    db.add(loan)
    loans.append(loan)
db.flush()
print(f"  ✅ {len(loans)} préstamos creados")

# Contratos
contract_count = 0
for _ in range(400):
    inst = random.choice(institutions)
    comp = random.choice(companies)
    monto = rand_monto()
    fecha = rand_date()
    num_adendas = random.choices([0, 0, 0, 1, 2, 3, 5], weights=[50, 20, 15, 8, 4, 2, 1])[0]
    incremento = num_adendas * random.uniform(3, 15) if num_adendas > 0 else 0
    financiado = random.random() < 0.15
    modalidad = random.choice(MODALIDADES)

    c = Contract(
        numero_contrato=f"CON-{inst.siglas}-{random.randint(1000, 9999)}-{fecha.year}",
        numero_proceso=f"PROC-{random.randint(10000, 99999)}",
        institution_id=inst.id,
        company_id=comp.id,
        loan_id=random.choice(loans).id if financiado else None,
        descripcion=random.choice([
            "Construcción de acueducto", "Suministro de equipos médicos",
            "Servicios de consultoría", "Mantenimiento de red vial",
            "Construcción de escuela", "Adquisición de materiales",
            "Servicios de tecnología", "Construcción de planta de tratamiento",
            "Suministro de medicamentos", "Rehabilitación de carretera",
        ]),
        modalidad=modalidad,
        monto_original=monto,
        monto_actual=monto * (1 + incremento / 100) if incremento > 0 else monto,
        moneda="DOP",
        fecha_firma=fecha,
        fecha_inicio=fecha + timedelta(days=30),
        fecha_fin_planificada=fecha + timedelta(days=365),
        oficial_firmante=random.choice(["Lic. Roberto Muñoz", "Ing. Carmen Soto", "Dr. Luis Martínez"]),
        tiene_adendas=num_adendas > 0,
        num_adendas=num_adendas,
        incremento_porcentual=round(incremento, 2),
        financiado_prestamo=financiado,
        es_mayor_100m=monto >= 100_000_000,
        retraso_dias=random.choice([0, 0, 0, 30, 60, 120, 365]),
        fuente="Demo Data",
    )
    db.add(c)
    contract_count += 1
db.flush()
print(f"  ✅ {contract_count} contratos creados")

# Actualizar stats de empresas e instituciones
from sqlalchemy import func
for comp in companies:
    r = db.query(func.count(Contract.id), func.sum(Contract.monto_original),
                 func.count(func.distinct(Contract.institution_id)))\
         .filter(Contract.company_id == comp.id).first()
    if r:
        comp.total_contratos = r[0] or 0
        comp.total_monto_recibido = r[1] or 0
        comp.total_instituciones = r[2] or 0

for inst in institutions:
    r = db.query(func.count(Contract.id), func.sum(Contract.monto_original))\
         .filter(Contract.institution_id == inst.id).first()
    if r:
        inst.total_contratos = r[0] or 0
        inst.total_monto_contratos = r[1] or 0

db.commit()
db.close()

print("")
print("═══════════════════════════════════════════")
print("  ✅ Demo sembrada exitosamente")
print("  Ahora ejecuta el scan de alertas:")
print("  curl -X POST http://localhost:8000/api/alerts/scan")
print("═══════════════════════════════════════════")
