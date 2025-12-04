from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReportBase(BaseModel):
    tipo: str
    descripcion: str
    latitud: Optional[str] = None
    longitud: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportUpdate(BaseModel):
    resuelto: bool

class ReportResponse(ReportBase):
    id: int
    id_usuario: Optional[int] = None
    resuelto: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True
