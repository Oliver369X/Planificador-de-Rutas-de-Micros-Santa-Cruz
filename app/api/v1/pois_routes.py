from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from typing import List, Optional
from app.schemas.poi import POICreate, POIResponse, POIUpdate
from app.crud.poi import crud_poi
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/pois", tags=["pois"])

@router.post("/", response_model=POIResponse, status_code=status.HTTP_201_CREATED)
def create_poi(
    poi: POICreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear POI (Admin)"""
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    return crud_poi.create(db, poi)

@router.put("/{id}", response_model=POIResponse)
def update_poi(
    id: int,
    poi: POIUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar POI (Admin)"""
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    db_poi = crud_poi.get_by_id(db, id)
    if not db_poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")
    
    return crud_poi.update(db, db_poi, poi)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poi(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Eliminar POI (Admin)"""
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    db_poi = crud_poi.get_by_id(db, id)
    if not db_poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")
    
    crud_poi.delete(db, db_poi)

@router.get("/categories")
def get_poi_categories(db: Session = Depends(get_db)):
    """Obtiene todas las categorías de POIs disponibles"""
    query = text("SELECT DISTINCT tipo FROM transporte.points_of_interest ORDER BY tipo")
    results = db.execute(query).fetchall()
    return [r.tipo for r in results]

@router.get("/")
def get_pois(
    category: Optional[str] = Query(None, description="Filtrar por categoría (tipo)"),
    limit: int = Query(100, description="Límite de resultados"),
    db: Session = Depends(get_db)
):
    """
    Obtiene POIs, opcionalmente filtrados por categoría.
    Devuelve GeoJSON.
    """
    sql = """
        SELECT 
            objectid, nombre, tipo, subtipo, latitud, longitud, direccion
        FROM transporte.points_of_interest
    """
    params = {"limit": limit}
    
    if category:
        sql += " WHERE tipo = :category"
        params["category"] = category
        
    sql += " LIMIT :limit"
    
    results = db.execute(text(sql), params).fetchall()
    
    features = []
    for r in results:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(r.longitud), float(r.latitud)]
            },
            "properties": {
                "id": r.objectid,
                "nombre": r.nombre,
                "tipo": r.tipo,
                "subtipo": r.subtipo,
                "direccion": r.direccion
            }
        })
        
    return {"type": "FeatureCollection", "features": features}
