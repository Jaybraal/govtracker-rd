from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Official(Base):
    __tablename__ = "funcionarios"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    nombre = Column(String(500), nullable=False, index=True)
    cedula = Column(String(20), index=True)
    cargo = Column(String(300))
    email = Column(String(200))
    telefono = Column(String(50))
    activo = Column(Boolean, default=True)
    fecha_inicio = Column(DateTime(timezone=True))
    fecha_fin = Column(DateTime(timezone=True))
    total_contratos_aprobados = Column(Integer, default=0)
    total_monto_aprobado = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    institution = relationship("Institution", back_populates="officials")
