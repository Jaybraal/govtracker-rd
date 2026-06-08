from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Company(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    rnc = Column(String(20), unique=True, index=True)
    rpe = Column(String(20), unique=True, index=True)  # Registro de Proveedores del Estado (DGCP)
    nombre = Column(String(500), nullable=False, index=True)
    nombre_comercial = Column(String(500))
    tipo_empresa = Column(String(100))  # SRL, SA, EIRL, etc.
    sector = Column(String(200))
    telefono = Column(String(50))
    email = Column(String(200))
    direccion = Column(Text)
    provincia = Column(String(100))
    pais = Column(String(100), default="República Dominicana")
    activo = Column(Boolean, default=True)
    # Métricas calculadas
    total_contratos = Column(Integer, default=0)
    total_monto_recibido = Column(Float, default=0)
    total_instituciones = Column(Integer, default=0)
    primer_contrato = Column(DateTime(timezone=True))
    ultimo_contrato = Column(DateTime(timezone=True))
    indice_concentracion = Column(Float, default=0)  # % de contratos en 1 institución
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contracts = relationship("Contract", back_populates="company")
    legal_representatives = relationship("LegalRepresentative", back_populates="company")


class LegalRepresentative(Base):
    __tablename__ = "representantes_legales"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(500), nullable=False, index=True)
    cedula = Column(String(20), index=True)
    cargo = Column(String(200))
    email = Column(String(200))
    telefono = Column(String(50))
    activo = Column(Boolean, default=True)
    total_empresas = Column(Integer, default=1)  # Cuántas empresas representa
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="legal_representatives")


class SupplierDisqualification(Base):
    """Registro oficial de Proveedores del Estado Inhabilitados (DGCP/SECP)."""
    __tablename__ = "proveedores_inhabilitados"

    id = Column(Integer, primary_key=True, index=True)
    rpe = Column(String(20), index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("empresas.id"), index=True)
    motivo = Column(Text)
    fecha_inhabilitacion = Column(DateTime(timezone=True))
    fecha_habilitacion = Column(DateTime(timezone=True))
    oficio_inhabilitacion = Column(String(200))
    url_certificacion = Column(String(500))
    fuente = Column(String(200))
    url_fuente = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company")
