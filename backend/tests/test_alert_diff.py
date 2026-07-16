from datetime import datetime, timedelta, timezone

from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.alert_diff import get_new_alerts


def _alert(db, *, created_at, severidad=AlertSeverity.MEDIA, titulo="x"):
    a = Alert(
        tipo=AlertType.CONTRATO_GRANDE, severidad=severidad, titulo=titulo,
        entidad_tipo="contrato", entidad_id=1, created_at=created_at,
    )
    db.add(a)
    db.commit()
    return a


def test_solo_devuelve_alertas_posteriores_a_since(db_session):
    corte = datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc)
    _alert(db_session, created_at=corte - timedelta(days=1), titulo="vieja")
    nueva = _alert(db_session, created_at=corte + timedelta(minutes=1), titulo="nueva")

    resultado = get_new_alerts(db_session, since=corte)

    assert [a.titulo for a in resultado] == ["nueva"]


def test_ordena_por_severidad_critica_primero(db_session):
    corte = datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc)
    _alert(db_session, created_at=corte + timedelta(minutes=1), severidad=AlertSeverity.MEDIA, titulo="media")
    _alert(db_session, created_at=corte + timedelta(minutes=2), severidad=AlertSeverity.CRITICA, titulo="critica")
    _alert(db_session, created_at=corte + timedelta(minutes=3), severidad=AlertSeverity.ALTA, titulo="alta")

    resultado = get_new_alerts(db_session, since=corte)

    assert [a.titulo for a in resultado] == ["critica", "alta", "media"]
