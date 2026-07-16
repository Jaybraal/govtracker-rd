"""
Entrypoint del cron diario (ver .github/workflows/investigar.yml). Se
ejecuta con:
    python -m scripts.investigar
Un fallo de UNA fuente no hace fallar el script completo — eso ya lo
tolera el orquestador y queda registrado en `etl_runs`. El script solo
devuelve código distinto de 0 si algo revienta fuera de ese manejo (bug
real, no un portal caído).
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger

from app.core.database import SessionLocal, Base, engine
import app.models  # noqa: F401 — registra todos los modelos antes de create_all
from app.etl.orchestrator import run_daily, DailySource
from app.services.alert_scanner import run_alert_scan
from app.services.alert_diff import get_new_alerts
from app.services.digest import build_digest
from app.services.notifier import get_notifiers


async def main(
    sources: Optional[list[DailySource]] = None,
    notifiers_override: Optional[list] = None,
) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Margen de seguridad: `Alert.created_at` usa `server_default=func.now()`,
    # que en SQLite se trunca a resolución de segundo completo (sin
    # microsegundos). Si tomáramos `datetime.now()` con microsegundos justo
    # antes de `run_alert_scan`, una alerta creada en el MISMO segundo
    # quedaría con un `created_at` truncado "menor" que `inicio`, y
    # `get_new_alerts` (que filtra con `created_at > since`) la perdería en
    # silencio. Restar 2s cubre esa pérdida de precisión sin riesgo real de
    # reenviar alertas viejas — `alert_scanner` ya deduplica por
    # (tipo, entidad_id), así que una alerta preexistente no se recrea.
    inicio = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=2)
    try:
        resultados = await run_daily(db, sources=sources)
        for r in resultados:
            detalle = f" — {r.error}" if r.error else ""
            logger.info(f"{r.fuente}: {r.estado} ({r.registros_nuevos} nuevos){detalle}")

        run_alert_scan(db)

        nuevas = get_new_alerts(db, since=inicio)
        texto = build_digest(nuevas)
        notifiers = notifiers_override if notifiers_override is not None else get_notifiers()
        if texto:
            for notifier in notifiers:
                try:
                    notifier.send(texto)
                except Exception as e:
                    logger.error(f"Notificador {type(notifier).__name__} falló: {e}")
        else:
            logger.info("Sin hallazgos nuevos — no se envía nada.")

        fallos = [r for r in resultados if r.estado == "error"]
        if fallos:
            logger.warning(f"{len(fallos)} fuente(s) fallaron esta corrida: {[r.fuente for r in fallos]}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
