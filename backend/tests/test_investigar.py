from datetime import datetime, timezone

from app.etl.orchestrator import DailySource
from app.models.contract import Contract, ContractStatus
from scripts.investigar import main


def _seed_contrato_que_dispara_alerta(db):
    """CONTRATO_GRANDE: monto >= 100M vía contratación directa — regla #1
    de alert_scanner.py, la más simple de disparar sin datos externos."""
    c = Contract(
        numero_contrato="TEST-001", modalidad="contratacion_directa",
        monto_original=150_000_000, moneda="DOP", estado=ContractStatus.ACTIVO,
        institution_id=1, company_id=1,
    )
    db.add(c)
    db.commit()


class FakeNotifier:
    def __init__(self):
        self.enviados = []
    def send(self, text):
        self.enviados.append(text)


async def test_main_envia_digest_cuando_hay_alertas_nuevas(db_session, monkeypatch):
    monkeypatch.setattr("scripts.investigar.SessionLocal", lambda: db_session)
    monkeypatch.setattr("scripts.investigar.Base", type("B", (), {"metadata": type("M", (), {"create_all": lambda **k: None})}))

    _seed_contrato_que_dispara_alerta(db_session)
    fake = FakeNotifier()

    codigo = await main(sources=[], notifiers_override=[fake])

    assert codigo == 0
    assert len(fake.enviados) == 1
    assert "CONTRATO_GRANDE" in fake.enviados[0] or "Contrato directo" in fake.enviados[0]


async def test_main_no_envia_nada_sin_hallazgos_nuevos(db_session, monkeypatch):
    monkeypatch.setattr("scripts.investigar.SessionLocal", lambda: db_session)
    monkeypatch.setattr("scripts.investigar.Base", type("B", (), {"metadata": type("M", (), {"create_all": lambda **k: None})}))

    fake = FakeNotifier()
    codigo = await main(sources=[], notifiers_override=[fake])

    assert codigo == 0
    assert fake.enviados == []
