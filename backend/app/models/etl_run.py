from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from ..core.database import Base


class EtlRun(Base):
    """
    Historial de ejecuciones de scrapers/ETL. Antes el estado de cada corrida
    vivía solo en memoria (`_pipeline_status` en etl.py) y se perdía al
    reiniciar el servidor — no había forma de saber con certeza cuándo fue
    la última actualización real de una fuente. Esta tabla persiste cada
    corrida para responder esa pregunta de forma auditable.
    """
    __tablename__ = "etl_runs"

    id = Column(Integer, primary_key=True, index=True)
    fuente = Column(String(100), nullable=False, index=True)
    iniciado_en = Column(DateTime(timezone=True), server_default=func.now())
    finalizado_en = Column(DateTime(timezone=True))
    estado = Column(String(20), default="ok")  # ok | error | parcial
    registros_nuevos = Column(Integer, default=0)
    alertas_nuevas = Column(Integer, default=0)
    detalle = Column(JSON)
    error = Column(Text)
