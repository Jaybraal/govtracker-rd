from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class BankType(str, enum.Enum):
    BANCO_MULTIPLE      = "banco_multiple"
    BANCO_AHORRO_CREDITO = "banco_ahorro_credito"
    BANCO_CREDITO       = "banco_credito"
    ASOCIACION_AHORRO   = "asociacion_ahorro"
    BANCO_ESTATAL       = "banco_estatal"
    BANCO_EXTRANJERO    = "banco_extranjero"


class Bank(Base):
    __tablename__ = "bancos"

    id = Column(Integer, primary_key=True, index=True)

    # Identificación
    codigo_sib          = Column(String(20), unique=True, index=True)  # Cód. Superintendencia
    rnc                 = Column(String(20), unique=True, index=True)
    nombre              = Column(String(500), nullable=False, index=True)
    nombre_corto        = Column(String(100))
    tipo                = Column(Enum(BankType), default=BankType.BANCO_MULTIPLE)
    es_estatal          = Column(Boolean, default=False)

    # Info
    pais_origen         = Column(String(100), default="República Dominicana")
    ano_fundacion       = Column(Integer)
    sitio_web           = Column(String(500))
    telefono            = Column(String(50))
    direccion_principal = Column(Text)
    num_sucursales      = Column(Integer, default=0)
    num_empleados       = Column(Integer, default=0)

    # Balance financiero (último año disponible)
    anio_balance        = Column(Integer)
    activos_totales     = Column(Float, default=0)   # RD$
    pasivos_totales     = Column(Float, default=0)
    patrimonio          = Column(Float, default=0)
    cartera_creditos    = Column(Float, default=0)   # Préstamos otorgados
    depositos_totales   = Column(Float, default=0)
    utilidad_neta       = Column(Float, default=0)
    indice_solvencia    = Column(Float, default=0)   # % capital/activos riesgo
    mora_porcentaje     = Column(Float, default=0)   # % cartera en mora
    roa                 = Column(Float, default=0)   # Retorno sobre activos
    roe                 = Column(Float, default=0)   # Retorno sobre patrimonio

    # Relación con el Estado
    custodia_fondos_estado  = Column(Boolean, default=False)
    monto_fondos_estado     = Column(Float, default=0)   # Depósitos del gobierno
    num_cuentas_instituciones = Column(Integer, default=0)
    es_banco_pagador        = Column(Boolean, default=False)  # Paga nómina estatal

    fuente      = Column(String(500))
    url_fuente  = Column(String(1000))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    company_accounts = relationship("CompanyBankAccount", back_populates="bank")
    institution_accounts = relationship("InstitutionBankAccount", back_populates="bank")


class CompanyBankAccount(Base):
    """Vincula empresas contratistas con su banco domiciliario."""
    __tablename__ = "cuentas_empresas_banco"

    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    bank_id     = Column(Integer, ForeignKey("bancos.id"), nullable=False)
    tipo_cuenta = Column(String(100))   # corriente, ahorro, etc.
    fuente      = Column(String(200))   # de qué documento se extrajo
    verificado  = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    bank    = relationship("Bank", back_populates="company_accounts")


class InstitutionBankAccount(Base):
    """Qué banco custodia fondos de cada institución del Estado."""
    __tablename__ = "cuentas_instituciones_banco"

    id              = Column(Integer, primary_key=True, index=True)
    institution_id  = Column(Integer, ForeignKey("instituciones.id"), nullable=False)
    bank_id         = Column(Integer, ForeignKey("bancos.id"), nullable=False)
    descripcion     = Column(String(500))
    monto_depositado = Column(Float, default=0)
    tipo_fondo      = Column(String(200))  # presupuesto, FIDE, especial, etc.
    fuente          = Column(String(200))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    bank = relationship("Bank", back_populates="institution_accounts")
