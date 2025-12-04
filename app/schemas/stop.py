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

from pydantic import BaseModel, Field

class StopResponse(StopBase):
    id_parada: int
    # Mapear nombre_parada del modelo a nombre del schema
    nombre: str = Field(validation_alias="nombre_parada")
    activa: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True
