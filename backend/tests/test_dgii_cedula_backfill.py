import pytest

from app.models.company import Company, LegalRepresentative
from app.etl.scrapers.dgii_scraper import DGIIScraper


@pytest.mark.asyncio
async def test_backfillea_cedula_en_representante_existente_sin_cedula(db_session, monkeypatch):
    comp = Company(nombre="Empresa Test", rnc="123456789")
    db_session.add(comp)
    db_session.commit()

    rep = LegalRepresentative(company_id=comp.id, nombre="Juan Pérez", cedula="")
    db_session.add(rep)
    db_session.commit()

    scraper = DGIIScraper()
    monkeypatch.setattr(scraper, "db", db_session)

    await scraper._update_company(comp, {"representante": "Juan Pérez", "cedula_repr": "001-1234567-8"})
    db_session.commit()

    db_session.refresh(rep)
    assert rep.cedula == "001-1234567-8"


@pytest.mark.asyncio
async def test_no_pisa_cedula_ya_correcta_con_vacio(db_session, monkeypatch):
    comp = Company(nombre="Empresa Test 2", rnc="987654321")
    db_session.add(comp)
    db_session.commit()

    rep = LegalRepresentative(company_id=comp.id, nombre="Ana Gómez", cedula="001-9999999-9")
    db_session.add(rep)
    db_session.commit()

    scraper = DGIIScraper()
    monkeypatch.setattr(scraper, "db", db_session)

    await scraper._update_company(comp, {"representante": "Ana Gómez", "cedula_repr": ""})
    db_session.commit()

    db_session.refresh(rep)
    assert rep.cedula == "001-9999999-9"
