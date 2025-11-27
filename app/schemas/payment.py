from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class PaymentBase(BaseModel):
    tipo: str
    monto: Decimal
    descripcion: Optional[str] = None

class PaymentCreate(PaymentBase):
    id_usuario: int

class PaymentResponse(PaymentBase):
    id_pago: int
    id_usuario: int
    fecha_hora: datetime
    
    class Config:
        from_attributes = True
