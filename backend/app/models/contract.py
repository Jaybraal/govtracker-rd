from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class ContractStatus(str, enum.Enum):
    ACTIVO = "activo"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"
    SUSPENDIDO = "suspendido"
    EN_LITIGIO = "en_litigio"


class ModalidadCompra(str, enum.Enum):
    LICITACION_PUBLICA = "licitacion_publica"
    LICITACION_RESTRINGIDA = "licitacion_restringida"
    SORTEO = "sorteo"
    COMPARACION_PRECIOS = "comparacion_precios"
    CONTRATACION_DIRECTA = "contratacion_directa"
    SUBASTA_INVERSA = "subasta_inversa"
    ACUERDO_MARCO = "acuerdo_marco"
    OTRO = "otro"


class Contract(Base):
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    numero_contrato = Column(String(200), unique=True, index=True)
    numero_proceso = Column(String(200), index=True)
    institution_id = Column(Integer, ForeignKey("instituciones.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("proyectos.id"), nullable=True)
    loan_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True)

    descripcion = Column(Text)
    objeto = Column(Text)
    modalidad = Column(Enum(ModalidadCompra))
    estado = Column(Enum(ContractStatus), default=ContractStatus.ACTIVO)

    # Montos
    monto_original = Column(Float, nullable=False)
    monto_actual = Column(Float)         # Después de adendas
    monto_pagado = Column(Float, default=0)
    moneda = Column(String(10), default="DOP")

    # Fechas
    fecha_firma = Column(DateTime(timezone=True))
    fecha_inicio = Column(DateTime(timezone=True))
    fecha_fin_planificada = Column(DateTime(timezone=True))
    fecha_fin_real = Column(DateTime(timezone=True))

    # Funcionario que aprobó
    oficial_firmante = Column(String(500))
    oficial_aprobador = Column(String(500))

    # Banderas de riesgo
    tiene_adendas = Column(Boolean, default=False)
    num_adendas = Column(Integer, default=0)
    incremento_porcentual = Column(Float, default=0)
    retraso_dias = Column(Integer, default=0)
    financiado_prestamo = Column(Boolean, default=False)
    es_mayor_100m = Column(Boolean, default=False)
    fuente = Column(String(500))
    url_fuente = Column(String(1000))
    raw_data = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    institution = relationship("Institution", back_populates="contracts")
    company = relationship("Company", back_populates="contracts")
    project = relationship("Project", back_populates="contracts")
    loan = relationship("Loan", back_populates="contracts")
    addenda = relationship("Addendum", back_populates="contract")
    payments = relationship("Payment", back_populates="contract")
    documents = relationship("Document", back_populates="contract")


class Addendum(Base):
    __tablename__ = "adendas"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contratos.id"), nullable=False)
    numero = Column(Integer)
    descripcion = Column(Text)
    monto_adicional = Column(Float, default=0)
    dias_adicionales = Column(Integer, default=0)
    fecha = Column(DateTime(timezone=True))
    justificacion = Column(Text)
    url_documento = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="addenda")


class Payment(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contratos.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(DateTime(timezone=True))
    descripcion = Column(Text)
    numero_cheque = Column(String(100))
    fuente = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="payments")
