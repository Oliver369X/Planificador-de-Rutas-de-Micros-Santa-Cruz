"""
Endpoints compatibles con Photon API para trufi-core
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from typing import Optional

router = APIRouter(tags=["Photon Compatible"])

@router.get("/api")
def photon_search(
    q: str = Query(..., description="Término de búsqueda"),
    limit: int = Query(15),
    bbox: Optional[str] = Query(None, description="Bounding box (ignorado, usamos Santa Cruz)"),
    db: Session = Depends(get_db)
):
    """
    Búsqueda de lugares compatible con Photon API.
    trufi-core llama a $photonUrl/api?q=...
    """
    search_term = f"%{q}%"
    
    # Buscar en POIs
    pois_query = text("""
        SELECT objectid as id, nombre, tipo, latitud, longitud, direccion
        FROM transporte.points_of_interest
        WHERE nombre ILIKE :query
        LIMIT :limit
    """)
    
    # Buscar en Paradas
    stops_query = text("""
        SELECT id_parada as id, nombre_parada as nombre, 'parada' as tipo,
               latitud, longitud, '' as direccion
        FROM transporte.paradas
        WHERE nombre_parada ILIKE :query
        LIMIT :limit
    """)
    
    pois = db.execute(pois_query, {"query": search_term, "limit": limit}).fetchall()
    stops = db.execute(stops_query, {"query": search_term, "limit": limit}).fetchall()
    
    features = []
    
    for p in pois:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(p.longitud), float(p.latitud)]
            },
            "properties": {
                "osm_id": p.id,
                "osm_type": "N",
                "name": p.nombre,
                "street": p.direccion or "",
                "city": "Santa Cruz de la Sierra",
                "country": "Bolivia",
                "osm_key": "amenity",
                "osm_value": p.tipo
            }
        })
        
    for s in stops:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(s.longitud), float(s.latitud)]
            },
            "properties": {
                "osm_id": s.id,
                "osm_type": "N",
                "name": s.nombre,
                "street": "Parada de Micro",
                "city": "Santa Cruz de la Sierra",
                "country": "Bolivia",
                "osm_key": "highway",
                "osm_value": "bus_stop"
            }
        })
        
    return {"type": "FeatureCollection", "features": features}

@router.get("/reverse")
def photon_reverse(
    lat: float = Query(...),
    lon: float = Query(...),
    db: Session = Depends(get_db)
):
    """
    Reverse geocoding compatible con Photon API.
    trufi-core llama a $photonUrl/reverse?lat=...&lon=...
    """
    query = text("""
        SELECT objectid as id, nombre, tipo, latitud, longitud, direccion,
               ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) as distance
        FROM transporte.points_of_interest
        ORDER BY distance ASC
        LIMIT 1
    """)
    
    result = db.execute(query, {"lat": lat, "lon": lon}).fetchone()
    
    features = []
    if result:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(result.longitud), float(result.latitud)]
            },
            "properties": {
                "osm_id": result.id,
                "osm_type": "N",
                "name": result.nombre,
                "street": result.direccion or "",
                "city": "Santa Cruz de la Sierra",
                "country": "Bolivia"
            }
        })
        
    return {"type": "FeatureCollection", "features": features}
