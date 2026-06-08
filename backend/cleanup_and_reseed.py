"""
Limpia los datos fabricados/ilustrativos sembrados anteriormente para los
sectores Combustibles, Seguros/SENASA y Seguridad, y vuelve a sembrar con
las versiones corregidas (datos reales y verificables).
"""
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite:///./govtracker_test.db"
os.environ["DATABASE_URL_ASYNC"] = "sqlite+aiosqlite:///./govtracker_test.db"

from app.core.database import SessionLocal
from app.models.company import Company, LegalRepresentative
from app.models.contract import Contract, Addendum, Payment
from app.models.document import Document

OLD_RNCS = [
    # combustibles (fabricados)
    "401001987", "131056789", "101089234", "101034567", "101045678",
    "101067890", "101078901", "401089123",
    # seguros/senasa (fabricados)
    "401050123", "401055890", "101023456", "101034789", "101045123",
    "101056234", "101067345", "101078456", "101089567", "101090678",
    # seguridad (fabricados)
    "101101234", "101112345", "101123456", "101134567", "101145678",
    "101156789",
]


def cleanup():
    db = SessionLocal()
    removed_companies = 0
    removed_contracts = 0
    for rnc in OLD_RNCS:
        comp = db.query(Company).filter(Company.rnc == rnc).first()
        if not comp:
            continue
        contratos = db.query(Contract).filter(Contract.company_id == comp.id).all()
        for ct in contratos:
            db.query(Payment).filter(Payment.contract_id == ct.id).delete()
            db.query(Addendum).filter(Addendum.contract_id == ct.id).delete()
            db.query(Document).filter(Document.contract_id == ct.id).delete()
            db.delete(ct)
            removed_contracts += 1
        db.query(LegalRepresentative).filter(LegalRepresentative.company_id == comp.id).delete()
        db.delete(comp)
        removed_companies += 1
    db.commit()
    db.close()
    print(f"Limpieza: {removed_companies} empresas fabricadas eliminadas, {removed_contracts} contratos asociados eliminados")


async def reseed():
    from app.etl.scrapers.combustibles_scraper import run_combustibles_scraper
    from app.etl.scrapers.seguros_senasa_scraper import run_seguros_senasa_scraper
    from app.etl.scrapers.seguridad_scraper import run_seguridad_scraper

    n1 = await run_combustibles_scraper()
    print(f"Combustibles (real): {n1} registros")
    n2 = await run_seguros_senasa_scraper()
    print(f"Seguros/SENASA (real): {n2} registros")
    n3 = await run_seguridad_scraper()
    print(f"Seguridad (real): {n3} registros")


def verify():
    db = SessionLocal()
    print("\n--- Verificación ---")
    for rnc in OLD_RNCS:
        comp = db.query(Company).filter(Company.rnc == rnc).first()
        if comp:
            print(f"  ⚠️ AÚN EXISTE empresa fabricada: {comp.nombre} (RNC {rnc})")
    nombres_nuevos = [
        "V Energy, S.A. (anteriormente Sunix Petroleum, S.R.L.)",
        "Khersum, S.R.L.", "Deleste, S.R.L.", "Farmacard, S.R.L.",
        "All About Security, RCF, S.R.L.", "Servicios Generales M.A., S.R.L.",
        "D'Tec (Defensa & Tecnología), S.R.L.", "Solutions 24/7 M&A, S.R.L.",
    ]
    for nombre in nombres_nuevos:
        comp = db.query(Company).filter(Company.nombre == nombre).first()
        if comp:
            contratos = db.query(Contract).filter(Contract.company_id == comp.id).all()
            total = sum(c.monto_original for c in contratos)
            print(f"  ✓ {comp.nombre}: {len(contratos)} contrato(s), total RD${total:,.2f}")
        else:
            print(f"  ✗ FALTA: {nombre}")
    db.close()


if __name__ == "__main__":
    cleanup()
    asyncio.run(reseed())
    verify()
