from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FavoriteBase(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    latitud: str
    longitud: str

class FavoriteCreate(FavoriteBase):
    pass

class FavoriteUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None

class FavoriteResponse(FavoriteBase):
    id: int
    id_usuario: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
