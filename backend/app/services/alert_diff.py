"""
Aísla qué alertas son NUEVAS desde la última corrida. Sin esto, notificar
cada día repetiría las 33,897 alertas históricas en vez de solo lo que
cambió hoy — el error #1 que mataría la utilidad del sistema (ver spec,
riesgo R1: fatiga de alertas).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.alert import Alert, AlertSeverity

_ORDEN_SEVERIDAD = {
    AlertSeverity.CRITICA: 0,
    AlertSeverity.ALTA: 1,
    AlertSeverity.MEDIA: 2,
    AlertSeverity.BAJA: 3,
}


def get_new_alerts(db: Session, since: datetime) -> list[Alert]:
    """Alertas creadas estrictamente después de `since`, ordenadas por
    severidad (CRÍTICA primero) y luego por fecha de creación."""
    alertas = db.query(Alert).filter(Alert.created_at > since).all()
    return sorted(alertas, key=lambda a: (_ORDEN_SEVERIDAD.get(a.severidad, 9), a.created_at))
