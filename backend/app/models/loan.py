from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Table, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base

# Tabla pivot préstamos <-> instituciones
prestamos_instituciones = Table(
    "prestamos_instituciones",
    Base.metadata,
    Column("prestamo_id", Integer, ForeignKey("prestamos.id")),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
)


class LoanStatus(str, enum.Enum):
    ACTIVO = "activo"
    COMPLETADO = "completado"
    EN_DESEMBOLSO = "en_desembolso"
    CANCELADO = "cancelado"


class Loan(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(200), unique=True, index=True)
    acreedor = Column(String(500), nullable=False, index=True)  # BID, Banco Mundial, FMI, etc.
    tipo_acreedor = Column(String(100))  # bilateral, multilateral, bono
    descripcion = Column(Text)
    objeto = Column(Text)
    estado = Column(Enum(LoanStatus), default=LoanStatus.ACTIVO)

    # Montos
    monto_aprobado = Column(Float)
    monto_desembolsado = Column(Float, default=0)
    moneda = Column(String(10), default="USD")
    tasa_interes = Column(Float)
    plazo_anos = Column(Integer)
    periodo_gracia_anos = Column(Integer)

    # Fechas
    fecha_aprobacion = Column(DateTime(timezone=True))
    fecha_primer_desembolso = Column(DateTime(timezone=True))
    fecha_vencimiento = Column(DateTime(timezone=True))

    # Resolución del Congreso
    resolucion_congreso = Column(String(200))
    fecha_resolucion = Column(String(100))

    fuente = Column(String(500))
    url_fuente = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contracts = relationship("Contract", back_populates="loan")
    institutions = relationship("Institution", secondary=prestamos_instituciones, back_populates="loans")
    projects = relationship("Project", back_populates="loan")
