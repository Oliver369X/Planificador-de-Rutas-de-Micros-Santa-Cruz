from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StopBase(BaseModel):
    nombre: str
    latitud: float
    longitud: float
    descripcion: Optional[str] = None

class StopCreate(StopBase):
    pass

class StopUpdate(BaseModel):
    nombre: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    descripcion: Optional[str] = None
    activa: Optional[bool] = None

class StopResponse(StopBase):
    id_parada: int
    activa: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True
