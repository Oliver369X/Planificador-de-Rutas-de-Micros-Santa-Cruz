from pydantic import BaseModel, Field
from typing import Optional, List

class PatternStopCreate(BaseModel):
    id_parada: int
    sequence: int

class PatternStopResponse(BaseModel):
    id: int
    id_parada: int
    sequence: int
    nombre_parada: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    
    class Config:
        from_attributes = True

class PatternBase(BaseModel):
    name: str
    code: Optional[str] = None
    sentido: str

class PatternCreate(PatternBase):
    id_linea: int
    geometry_geojson: Optional[dict] = None

class PatternUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    sentido: Optional[str] = None
    geometry_geojson: Optional[dict] = None

class PatternResponse(PatternBase):
    id: str
    id_linea: int
    nombre_linea: Optional[str] = None
    short_name_linea: Optional[str] = None
    geometry_geojson: Optional[dict] = None
    stops: Optional[List[PatternStopResponse]] = []
    
    class Config:
        from_attributes = True

class PatternDetailResponse(PatternResponse):
    total_stops: int = 0
    route_length_km: Optional[float] = None
