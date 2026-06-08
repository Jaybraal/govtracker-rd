from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.contract import ContractStatus, ModalidadCompra


class ContractBase(BaseModel):
    numero_contrato: Optional[str]
    descripcion: Optional[str]
    objeto: Optional[str]
    modalidad: Optional[ModalidadCompra]
    estado: ContractStatus = ContractStatus.ACTIVO
    monto_original: float
    monto_actual: Optional[float]
    moneda: str = "DOP"
    fecha_firma: Optional[datetime]
    fecha_inicio: Optional[datetime]
    fecha_fin_planificada: Optional[datetime]
    oficial_firmante: Optional[str]


class ContractCreate(ContractBase):
    institution_id: int
    company_id: int


class ContractOut(ContractBase):
    id: int
    institution_id: int
    company_id: int
    monto_pagado: float
    tiene_adendas: bool
    num_adendas: int
    incremento_porcentual: float
    retraso_dias: int
    financiado_prestamo: bool
    es_mayor_100m: bool
    created_at: datetime
    # Nombres para UI
    empresa_nombre: Optional[str] = None
    institucion_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class ContractFilter(BaseModel):
    institution_id: Optional[int] = None
    company_id: Optional[int] = None
    modalidad: Optional[ModalidadCompra] = None
    estado: Optional[ContractStatus] = None
    monto_min: Optional[float] = None
    monto_max: Optional[float] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    financiado_prestamo: Optional[bool] = None
    tiene_adendas: Optional[bool] = None
    search: Optional[str] = None
