from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class POIBase(BaseModel):
    nombre: str
    tipo: str
    subtipo: Optional[str] = None
    latitud: str
    longitud: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    horario: Optional[str] = None
    distrito: Optional[str] = None
    poi_metadata: Optional[Dict[str, Any]] = None

class POICreate(POIBase):
    pass

class POIUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    subtipo: Optional[str] = None
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    horario: Optional[str] = None
    distrito: Optional[str] = None
    poi_metadata: Optional[Dict[str, Any]] = None
    activo: Optional[bool] = None

class POIResponse(POIBase):
    id: int
    objectid: Optional[int] = None
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True
