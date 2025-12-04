from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services.geocoding_service import geocoding_service

router = APIRouter(prefix="/geocode", tags=["Geocoding"])

@router.get("/search")
def search_places(
    q: str = Query(..., description="Término de búsqueda"),
    limit: int = Query(15, description="Límite de resultados"),
    db: Session = Depends(get_db)
):
    """
    Busca lugares por nombre (POIs y Paradas).
    Formato compatible con Photon.
    """
    return geocoding_service.search(db, q, limit)

@router.get("/reverse")
def reverse_geocode(
    lat: float = Query(..., description="Latitud"),
    lon: float = Query(..., description="Longitud"),
    db: Session = Depends(get_db)
):
    """
    Geocodificación inversa.
    """
    return geocoding_service.reverse(db, lat, lon)
