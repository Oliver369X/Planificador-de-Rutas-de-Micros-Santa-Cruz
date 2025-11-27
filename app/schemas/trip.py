from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TripRequest(BaseModel):
    origen_lat: float
    origen_lon: float
    destino_lat: float
    destino_lon: float

class TripResponse(BaseModel):
    id_viaje: int
    id_usuario: int
    origen_lat: float
    origen_lon: float
    destino_lat: float
    destino_lon: float
    tiempo_estimado_total: Optional[int]
    distancia_total: Optional[float]
    completado: bool
    fecha_hora: datetime
    
    class Config:
        from_attributes = True
