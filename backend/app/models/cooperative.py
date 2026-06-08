from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class CoopType(str, enum.Enum):
    AHORRO_CREDITO     = "ahorro_credito"
    AGROPECUARIA       = "agropecuaria"
    CONSUMO            = "consumo"
    VIVIENDA           = "vivienda"
    SERVICIOS_MULTIPLES = "servicios_multiples"
    ESCOLAR            = "escolar"
    TRANSPORTE         = "transporte"
    SALUD              = "salud"
    PRODUCCION         = "produccion"
    OTRO               = "otro"


class CoopStatus(str, enum.Enum):
    ACTIVA        = "activa"
    EN_LIQUIDACION = "en_liquidacion"
    SANCIONADA    = "sancionada"
    FUSIONADA     = "fusionada"
    INACTIVA      = "inactiva"


class Cooperative(Base):
    __tablename__ = "cooperativas"

    id = Column(Integer, primary_key=True, index=True)

    # Identificación
    numero_registro   = Column(String(100), unique=True, index=True)
    rnc               = Column(String(20),  unique=True, index=True)
    nombre            = Column(String(500), nullable=False, index=True)
    siglas            = Column(String(50))
    tipo              = Column(Enum(CoopType),   default=CoopType.OTRO)
    estado            = Column(Enum(CoopStatus), default=CoopStatus.ACTIVA)

    # Ubicación
    provincia  = Column(String(100))
    municipio  = Column(String(100))
    direccion  = Column(Text)
    telefono   = Column(String(50))
    email      = Column(String(200))
    sitio_web  = Column(String(500))

    # Directivos
    gerente_general     = Column(String(500))
    presidente_consejo  = Column(String(500))
    cedula_gerente      = Column(String(20))

    # Datos financieros (último año disponible)
    anio_balance        = Column(Integer)
    num_socios          = Column(Integer,  default=0)
    activos_totales     = Column(Float,    default=0)
    patrimonio          = Column(Float,    default=0)
    capital_social      = Column(Float,    default=0)
    cartera_creditos    = Column(Float,    default=0)  # Solo ahorro/crédito
    depositos           = Column(Float,    default=0)  # Solo ahorro/crédito
    ingresos            = Column(Float,    default=0)
    excedentes          = Column(Float,    default=0)

    # Fecha de constitución
    fecha_constitucion  = Column(DateTime(timezone=True))
    fecha_ultimo_balance = Column(DateTime(timezone=True))

    # Relación con Estado
    total_contratos_estado  = Column(Integer, default=0)
    total_monto_contratos   = Column(Float,   default=0)
    recibe_subsidio_estado  = Column(Boolean, default=False)
    prestamos_idecoop       = Column(Float,   default=0)

    fuente      = Column(String(500))
    url_fuente  = Column(String(1000))
    raw_data    = Column(JSON)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
