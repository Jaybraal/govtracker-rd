from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class ProjectStatus(str, enum.Enum):
    PLANIFICADO = "planificado"
    EN_EJECUCION = "en_ejecucion"
    COMPLETADO = "completado"
    SUSPENDIDO = "suspendido"
    CANCELADO = "cancelado"


class Project(Base):
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(200), unique=True, index=True)
    loan_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True)
    nombre = Column(String(1000), nullable=False, index=True)
    descripcion = Column(Text)
    sector = Column(String(200))
    estado = Column(Enum(ProjectStatus), default=ProjectStatus.EN_EJECUCION)
    provincia = Column(String(100))
    municipio = Column(String(100))
    latitud = Column(Float)
    longitud = Column(Float)

    monto_total = Column(Float)
    monto_ejecutado = Column(Float, default=0)
    porcentaje_avance = Column(Float, default=0)
    retraso_dias = Column(Integer, default=0)

    fecha_inicio_planificado = Column(DateTime(timezone=True))
    fecha_fin_planificado = Column(DateTime(timezone=True))
    fecha_inicio_real = Column(DateTime(timezone=True))
    fecha_fin_real = Column(DateTime(timezone=True))

    fuente = Column(String(500))
    url_fuente = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contracts = relationship("Contract", back_populates="project")
    loan = relationship("Loan", back_populates="projects")
