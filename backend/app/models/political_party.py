from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class PartyStatus(str, enum.Enum):
    ACTIVO      = "activo"
    INACTIVO    = "inactivo"
    EN_PROCESO  = "en_proceso"
    DISUELTO    = "disuelto"


class PartyIdeology(str, enum.Enum):
    CENTRO_DERECHA  = "centro_derecha"
    CENTRO          = "centro"
    CENTRO_IZQUIERDA = "centro_izquierda"
    DERECHA         = "derecha"
    IZQUIERDA       = "izquierda"
    POPULISTA       = "populista"
    OTRO            = "otro"


class PoliticalParty(Base):
    __tablename__ = "partidos_politicos"

    id = Column(Integer, primary_key=True, index=True)

    # Identificación
    codigo_jce      = Column(String(50), unique=True, index=True)
    rnc             = Column(String(20), index=True)
    nombre          = Column(String(500), nullable=False, index=True)
    siglas          = Column(String(30), index=True)
    color           = Column(String(20))        # color institucional hex
    estado          = Column(Enum(PartyStatus), default=PartyStatus.ACTIVO)
    ideologia       = Column(Enum(PartyIdeology), default=PartyIdeology.OTRO)

    # Liderazgo
    presidente_partido  = Column(String(500))
    secretario_general  = Column(String(500))
    candidato_presidencial = Column(String(500))

    # Historia
    fecha_fundacion     = Column(DateTime(timezone=True))
    fundador            = Column(String(500))
    sede_principal      = Column(Text)
    sitio_web           = Column(String(500))
    telefono            = Column(String(50))

    # Representación política actual
    senadores           = Column(Integer, default=0)
    diputados           = Column(Integer, default=0)
    sindicos            = Column(Integer, default=0)
    regidores           = Column(Integer, default=0)
    votos_ultimas_elecciones = Column(Float, default=0)   # porcentaje
    ano_ultimas_elecciones   = Column(Integer)

    # Financiamiento público (JCE) — acumulado
    total_financiamiento_jce  = Column(Float, default=0)  # RD$ total recibido
    financiamiento_anual_promedio = Column(Float, default=0)

    # Relación con contratos del Estado
    # (partidos también tienen RNC y pueden contratar)
    total_contratos_estado   = Column(Integer, default=0)
    total_monto_contratos    = Column(Float, default=0)

    fuente      = Column(String(500))
    url_fuente  = Column(String(1000))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    financiamientos = relationship("PartyFunding", back_populates="party")
    gastos          = relationship("PartyExpense",  back_populates="party")


class PartyFunding(Base):
    """Financiamiento anual del Estado a cada partido (JCE → Hacienda)."""
    __tablename__ = "financiamiento_partidos"

    id          = Column(Integer, primary_key=True, index=True)
    party_id    = Column(Integer, ForeignKey("partidos_politicos.id"), nullable=False)
    anio        = Column(Integer, nullable=False)
    trimestre   = Column(Integer)          # 1-4 o null si es anual
    monto       = Column(Float, nullable=False)
    concepto    = Column(String(500))      # aporte ordinario, campaña, etc.
    fuente_pago = Column(String(200))      # JCE, Tesorería Nacional, etc.
    banco_pago  = Column(String(200))      # banco donde se depositó
    resolucion  = Column(String(200))      # número de resolución JCE
    url_documento = Column(String(1000))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    party = relationship("PoliticalParty", back_populates="financiamientos")


class PartyExpense(Base):
    """Gastos declarados por los partidos ante la JCE."""
    __tablename__ = "gastos_partidos"

    id          = Column(Integer, primary_key=True, index=True)
    party_id    = Column(Integer, ForeignKey("partidos_politicos.id"), nullable=False)
    anio        = Column(Integer)
    categoria   = Column(String(300))   # publicidad, nómina, logística, etc.
    monto       = Column(Float)
    descripcion = Column(Text)
    proveedor   = Column(String(500))   # empresa contratada
    proveedor_rnc = Column(String(20))
    fuente      = Column(String(200))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    party = relationship("PoliticalParty", back_populates="gastos")
