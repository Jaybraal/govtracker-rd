from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Commission(Base):
    """
    Comisión del Congreso Nacional (Cámara de Diputados / bicamerales).
    Fuente: Sistema de Información Legislativa (SIL) — diputadosrd.gob.do/sil,
    API oficial en vivo (ver congreso_comisiones_scraper.py).

    Las comisiones permanentes son los órganos que estudian, dictaminan y
    aprueban (o rechazan) los proyectos de ley antes de pasar al Pleno; la
    "Comisión Coordinadora" cumple el rol de mesa directiva / agenda legislativa.
    """
    __tablename__ = "comisiones_congreso"

    id = Column(Integer, primary_key=True, index=True)

    comision_id_sil = Column(Integer, unique=True, index=True)
    nombre          = Column(String(500), nullable=False, index=True)
    tipo            = Column(String(100), index=True)  # Permanente, Especial, Bicameral, Coordinadora, ...
    tipo_id_sil     = Column(Integer, index=True)
    descripcion     = Column(Text)
    estado          = Column(String(50))
    fecha_designacion = Column(DateTime)

    fuente      = Column(String(500))
    url_fuente  = Column(String(1000))

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    miembros = relationship("CommissionMember", back_populates="comision", cascade="all, delete-orphan")


class CommissionMember(Base):
    """Miembro de una comisión del Congreso, con su cargo (Presidente/a, Vice-Presidente/a, Secretario/a, Miembro)."""
    __tablename__ = "comisiones_miembros"

    id = Column(Integer, primary_key=True, index=True)

    comision_id       = Column(Integer, ForeignKey("comisiones_congreso.id"), nullable=False, index=True)
    legislator_id     = Column(Integer, ForeignKey("legisladores.id"), index=True)
    legislador_id_sil = Column(Integer, index=True)
    nombre_completo   = Column(String(500))
    partido_siglas    = Column(String(30))
    cargo             = Column(String(50))
    estado            = Column(String(50))
    fecha_inicio      = Column(DateTime)
    fecha_fin         = Column(DateTime)

    comision   = relationship("Commission", back_populates="miembros")
    legislator = relationship("Legislator", back_populates="comisiones")
