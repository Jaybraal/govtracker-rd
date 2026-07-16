from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from ...core.database import get_db
from ...models.alert import Alert, AlertSeverity, AlertType
from ...services.alert_scanner import run_alert_scan as _scan_for_new_alerts

router = APIRouter(prefix="/alerts", tags=["Alertas"])


@router.get("/")
def list_alerts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, le=200),
    severidad: Optional[str] = None,
    tipo: Optional[str] = None,
    revisada: Optional[bool] = None,
    descartada: bool = False,
):
    q = db.query(Alert).filter(Alert.descartada == descartada)
    if severidad:
        q = q.filter(Alert.severidad == severidad)
    if tipo:
        q = q.filter(Alert.tipo == tipo)
    if revisada is not None:
        q = q.filter(Alert.revisada == revisada)
    total = q.count()
    items = q.order_by(desc(Alert.created_at)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
        "items": [_serialize(a) for a in items],
    }


@router.get("/stats")
def alert_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Alert.id)).filter(Alert.descartada == False).scalar()
    no_revisadas = db.query(func.count(Alert.id)).filter(
        Alert.revisada == False, Alert.descartada == False
    ).scalar()
    criticas = db.query(func.count(Alert.id)).filter(
        Alert.severidad == AlertSeverity.CRITICA, Alert.descartada == False
    ).scalar()
    por_tipo = db.query(
        Alert.tipo, func.count(Alert.id).label("cnt")
    ).filter(Alert.descartada == False).group_by(Alert.tipo).all()
    return {
        "total": total,
        "no_revisadas": no_revisadas,
        "criticas": criticas,
        "por_tipo": [{"tipo": r.tipo, "cantidad": r.cnt} for r in por_tipo],
    }


@router.post("/scan")
def run_alert_scan(db: Session = Depends(get_db)):
    """Ejecuta el scanner de alertas sobre los datos actuales."""
    nuevas = _scan_for_new_alerts(db)
    return {"message": f"{len(nuevas)} alertas generadas", "count": len(nuevas)}


@router.patch("/{alert_id}/review")
def review_alert(
    alert_id: int,
    notas: str = Body("", embed=True),
    db: Session = Depends(get_db),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(404, "Alerta no encontrada")
    alert.revisada = True
    alert.notas_revision = notas
    db.commit()
    return {"ok": True}


@router.patch("/{alert_id}/discard")
def discard_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.descartada = True
        db.commit()
    return {"ok": True}


def _serialize(a: Alert) -> dict:
    return {
        "id": a.id, "tipo": a.tipo, "severidad": a.severidad,
        "titulo": a.titulo, "descripcion": a.descripcion,
        "entidad_tipo": a.entidad_tipo, "entidad_id": a.entidad_id,
        "entidad_nombre": a.entidad_nombre, "monto_involucrado": a.monto_involucrado,
        "revisada": a.revisada, "descartada": a.descartada,
        "notas_revision": a.notas_revision, "datos_extra": a.datos_extra,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
