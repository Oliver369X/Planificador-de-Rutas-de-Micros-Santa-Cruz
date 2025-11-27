from pydantic import BaseModel
from typing import Optional

class RouteBase(BaseModel):
    id_linea: int
    id_parada: int
    sentido: str
    orden: int
    tiempo_estimado: Optional[int] = None

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    sentido: Optional[str] = None
    orden: Optional[int] = None
    tiempo_estimado: Optional[int] = None

class RouteResponse(RouteBase):
    id_recorrido: int
    
    class Config:
        from_attributes = True
