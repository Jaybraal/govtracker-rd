from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class InstitutionType(str, enum.Enum):
    MINISTERIO = "ministerio"
    EMPRESA_PUBLICA = "empresa_publica"
    ORGANISMO_AUTONOMO = "organismo_autonomo"
    MUNICIPIO = "municipio"
    PODER_JUDICIAL = "poder_judicial"
    CONGRESO = "congreso"
    OTRO = "otro"


class Institution(Base):
    __tablename__ = "instituciones"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True)
    nombre = Column(String(500), nullable=False, index=True)
    siglas = Column(String(50))
    tipo = Column(Enum(InstitutionType), default=InstitutionType.OTRO)
    descripcion = Column(Text)
    presupuesto_anual = Column(Float, default=0)
    sitio_web = Column(String(500))
    telefono = Column(String(50))
    direccion = Column(Text)
    activo = Column(Boolean, default=True)
    total_contratos = Column(Integer, default=0)
    total_monto_contratos = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contracts = relationship("Contract", back_populates="institution")
    officials = relationship("Official", back_populates="institution")
    audits = relationship("Audit", back_populates="institution")
    loans = relationship("Loan", secondary="prestamos_instituciones", back_populates="institutions")
