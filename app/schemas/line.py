from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LineBase(BaseModel):
    nombre: str
    color: Optional[str] = None
    descripcion: Optional[str] = None

class LineCreate(LineBase):
    pass

class LineUpdate(BaseModel):
    nombre: Optional[str] = None
    color: Optional[str] = None
    descripcion: Optional[str] = None
    activa: Optional[bool] = None

class LineResponse(LineBase):
    id_linea: int
    activa: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True
