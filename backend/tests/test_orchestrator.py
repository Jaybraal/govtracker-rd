import pytest

from app.etl.orchestrator import run_daily, DailySource, SourceResult
from app.models.etl_run import EtlRun


def _ok_sync(**kwargs):
    return {"contratos": 7}


async def _ok_async(**kwargs):
    return 3


def _fail_sync(**kwargs):
    raise RuntimeError("portal caído")


@pytest.mark.asyncio
async def test_run_daily_registra_etl_run_por_fuente(db_session):
    sources = [
        DailySource("fuente_ok", False, _ok_sync, {}, lambda r: r["contratos"]),
        DailySource("fuente_async_ok", True, _ok_async, {}, lambda r: r),
    ]
    resultados = await run_daily(db_session, sources=sources)

    assert resultados == [
        SourceResult(fuente="fuente_ok", estado="ok", registros_nuevos=7),
        SourceResult(fuente="fuente_async_ok", estado="ok", registros_nuevos=3),
    ]
    runs = db_session.query(EtlRun).order_by(EtlRun.id).all()
    assert [r.fuente for r in runs] == ["fuente_ok", "fuente_async_ok"]
    assert all(r.estado == "ok" and r.finalizado_en is not None for r in runs)


@pytest.mark.asyncio
async def test_un_fallo_no_detiene_las_demas_fuentes(db_session):
    sources = [
        DailySource("rota", False, _fail_sync, {}, lambda r: r),
        DailySource("sana", False, _ok_sync, {}, lambda r: r["contratos"]),
    ]
    resultados = await run_daily(db_session, sources=sources)

    assert resultados[0].estado == "error"
    assert "portal caído" in resultados[0].error
    assert resultados[1].estado == "ok"
    assert resultados[1].registros_nuevos == 7

    runs = {r.fuente: r for r in db_session.query(EtlRun).all()}
    assert runs["rota"].estado == "error"
    assert runs["sana"].estado == "ok"
