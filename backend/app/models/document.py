from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class DocType(str, enum.Enum):
    CONTRATO = "contrato"
    ADENDA = "adenda"
    AUDITORIA = "auditoria"
    PRESUPUESTO = "presupuesto"
    RESOLUCION = "resolucion"
    PRESTAMO = "prestamo"
    OTRO = "otro"


class Document(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contratos.id"), nullable=True)
    tipo = Column(Enum(DocType), default=DocType.OTRO)
    titulo = Column(String(1000))
    descripcion = Column(Text)
    url_original = Column(String(1000))
    archivo_local = Column(String(1000))
    formato = Column(String(20))  # pdf, xlsx, csv, docx
    texto_extraido = Column(Text)
    procesado = Column(Boolean, default=False)
    tamano_bytes = Column(Integer)
    hash_sha256 = Column(String(64))
    fuente = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="documents")
