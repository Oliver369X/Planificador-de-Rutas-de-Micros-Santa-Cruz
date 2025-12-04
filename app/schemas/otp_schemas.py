from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PlaceSchema(BaseModel):
    """Representa un lugar (origen, destino, parada)"""
    name: str = "Unknown"
    lat: float = Field(default=0.0)
    lon: float = Field(default=0.0)
    vertexType: str = "NORMAL"  # Añadido para OTP compat
    stopId: Optional[str] = None
    stopCode: Optional[str] = None
    platformCode: Optional[str] = None
    
    class Config:
        populate_by_name = True

class LegGeometry(BaseModel):
    """Geometría de un leg - REQUERIDO por trufi-core"""
    points: str = ""  # Encoded polyline
    length: int = 0

class LegSchema(BaseModel):
    """Segmento de un viaje (caminar, bus, etc)"""
    mode: str  # WALK, BUS, TRANSIT
    startTime: int  # milliseconds desde epoch
    endTime: int
    duration: float  # seconds (cambiado a float)
    distance: float  # meters
    from_: PlaceSchema = Field(default_factory=lambda: PlaceSchema(), alias="from")
    to: PlaceSchema = Field(default_factory=lambda: PlaceSchema())
    route: Optional[str] = ""
    routeId: Optional[str] = None
    routeShortName: Optional[str] = ""
    routeLongName: Optional[str] = ""
    routeColor: Optional[str] = "0088FF"
    routeTextColor: Optional[str] = "FFFFFF"
    agencyName: Optional[str] = "Transporte SC"
    legGeometry: LegGeometry = Field(default_factory=LegGeometry)  # CRÍTICO para trufi-core
    intermediateStops: List[PlaceSchema] = []
    # Campos boolean requeridos por trufi-core
    rentedBike: bool = False
    transitLeg: bool = False
    realTime: bool = False
    pathway: bool = False
    
    class Config:
        populate_by_name = True

class ItinerarySchema(BaseModel):
    """Un itinerario completo (una opción de ruta)"""
    legs: List[LegSchema]
    startTime: int  # milliseconds
    endTime: int
    duration: int  # seconds
    walkTime: int
    walkDistance: float
    transfers: int
    transitTime: int = 0
    waitingTime: int = 0
    elevationLost: float = 0.0
    elevationGained: float = 0.0
    tooSloped: bool = False

class PlanSchema(BaseModel):
    """Respuesta del endpoint /plan"""
    itineraries: List[ItinerarySchema] = []
    date: int = 0  # timestamp
    # IMPORTANTE: from y to nunca deben ser null, trufi-core espera objetos válidos
    from_: PlaceSchema = Field(default_factory=lambda: PlaceSchema(name="Origin"), alias="from")
    to: PlaceSchema = Field(default_factory=lambda: PlaceSchema(name="Destination"))
    
    class Config:
        populate_by_name = True


class PlanResponse(BaseModel):
    """Wrapper final para compatibilidad OTP"""
    plan: PlanSchema
    requestParameters: dict = {}

