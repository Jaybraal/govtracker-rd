from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class LegislatorChamber(str, enum.Enum):
    DIPUTADOS = "diputados"
    SENADO    = "senado"


class Legislator(Base):
    """
    Legislador del Congreso Nacional (Cámara de Diputados / Senado).
    Fuente: Sistema de Información Legislativa (SIL) — diputadosrd.gob.do/sil,
    API oficial en vivo de la Cámara de Diputados (ver camara_diputados_scraper.py).
    """
    __tablename__ = "legisladores"

    id = Column(Integer, primary_key=True, index=True)

    legislador_id_sil = Column(Integer, unique=True, index=True)  # ID en el SIL — permite re-sincronizar sin duplicar
    nombre_completo   = Column(String(500), nullable=False, index=True)
    camara            = Column(Enum(LegislatorChamber), nullable=False, index=True)
    funcion           = Column(String(50))   # texto tal cual lo reporta el SIL: "Diputado"/"Diputada"/"Senador"/"Senadora"

    partido_siglas    = Column(String(30),  index=True)
    partido_nombre    = Column(String(500))
    provincia         = Column(String(100), index=True)
    circunscripcion   = Column(String(200))

    # Cruce con contratos del Estado (detección de conflicto de interés —
    # mismo patrón que IdecoopScraper._cruzar_con_contratos): se llena solo si
    # se localiza una empresa cuyo nombre/RNC coincide con datos públicos del
    # legislador o sus familiares directos declarados oficialmente.
    total_contratos_relacionados = Column(Integer, default=0)
    total_monto_relacionado      = Column(Float,   default=0)

    fuente      = Column(String(500))
    url_fuente  = Column(String(1000))
    raw_data    = Column(JSON)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
