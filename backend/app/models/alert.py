from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, Enum, JSON
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class AlertSeverity(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class AlertType(str, enum.Enum):
    CONTRATO_GRANDE = "contrato_grande"
    EMPRESA_CONCENTRADA = "empresa_concentrada"
    MUCHAS_ADENDAS = "muchas_adendas"
    INCREMENTO_PRECIO = "incremento_precio"
    POSIBLE_CONFLICTO = "posible_conflicto"
    CONTRATO_DIRECTO = "contrato_directo"
    EMPRESA_MULTIPLE_MINISTERIOS = "empresa_multiple_ministerios"
    RETRASO_PROYECTO = "retraso_proyecto"
    REPRESENTANTE_MULTIPLE = "representante_multiple"
    PRESTAMO_DESEMBOLSO_RAPIDO = "prestamo_desembolso_rapido"
    ANOMALIA_MONTO = "anomalia_monto"
    EMPRESA_CAUTIVA = "empresa_cautiva"
    PROVEEDOR_INHABILITADO = "proveedor_inhabilitado"


class Alert(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(AlertType), nullable=False, index=True)
    severidad = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIA)
    titulo = Column(String(500), nullable=False)
    descripcion = Column(Text)
    entidad_tipo = Column(String(100))  # contrato, empresa, institución
    entidad_id = Column(Integer)
    entidad_nombre = Column(String(500))
    monto_involucrado = Column(Float)
    datos_extra = Column(JSON)
    revisada = Column(Boolean, default=False)
    descartada = Column(Boolean, default=False)
    notas_revision = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
