from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Audit(Base):
    __tablename__ = "auditorias"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    codigo = Column(String(200), index=True)
    titulo = Column(String(1000), nullable=False)
    tipo = Column(String(200))  # auditoría financiera, de desempeño, especial
    organismo_auditor = Column(String(500))  # Cámara de Cuentas, CGR, etc.
    periodo_auditado = Column(String(200))
    fecha_publicacion = Column(DateTime(timezone=True))
    resumen = Column(Text)
    hallazgos = Column(JSON)  # Lista de hallazgos estructurados
    monto_observado = Column(Float, default=0)
    monto_recuperado = Column(Float, default=0)
    num_hallazgos = Column(Integer, default=0)
    num_hallazgos_criticos = Column(Integer, default=0)
    url_informe = Column(String(1000))
    archivo_local = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    institution = relationship("Institution", back_populates="audits")
