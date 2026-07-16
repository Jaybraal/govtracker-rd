import pytest
from app.etl.pipeline import ETLPipeline


def test_dgcp_bulk_y_hacienda_ejecucion_estan_registrados():
    assert "dgcp_bulk" in ETLPipeline.ALL_SOURCES
    assert "hacienda_ejecucion" in ETLPipeline.ALL_SOURCES


def test_run_incremental_solo_corre_fuentes_diarias(monkeypatch):
    llamadas = []

    async def fake_run_full(self, sources=None):
        llamadas.append(sources)
        return {}

    monkeypatch.setattr(ETLPipeline, "run_full", fake_run_full)

    import asyncio
    asyncio.get_event_loop().run_until_complete(ETLPipeline().run_incremental())

    assert llamadas[0] == ETLPipeline.DAILY_SOURCES
    assert "seguridad" not in llamadas[0]  # fuente semilla estática, no diaria
