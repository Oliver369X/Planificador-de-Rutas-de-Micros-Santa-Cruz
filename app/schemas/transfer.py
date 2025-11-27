from pydantic import BaseModel
from typing import Optional

class TransferBase(BaseModel):
    id_viaje: int
    id_linea_origen: int
    id_linea_destino: int
    id_parada: int
    tiempo_estimado_trasbordo: Optional[int] = None

class TransferCreate(TransferBase):
    pass

class TransferUpdate(BaseModel):
    tiempo_estimado_trasbordo: Optional[int] = None

class TransferResponse(TransferBase):
    id_trasbordo: int
    
    class Config:
        from_attributes = True
