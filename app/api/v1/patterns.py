from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.pattern import *
from app.crud.pattern import crud_pattern
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/patterns", tags=["patterns"])

@router.get("/", response_model=List[PatternResponse])
def get_all_patterns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    patterns = crud_pattern.get_all(db, skip=skip, limit=limit)
    
    result = []
    for pattern in patterns:
        pattern_dict = {
            "id": pattern.id,
            "name": pattern.name,
            "code": pattern.code,
            "sentido": pattern.sentido,
            "id_linea": pattern.id_linea,
            "nombre_linea": pattern.linea.nombre if pattern.linea else None,
            "short_name_linea": pattern.linea.short_name if pattern.linea else None,
        }
        
        geometry = crud_pattern.get_geometry_geojson(db, pattern.id)
        if geometry:
            pattern_dict["geometry_geojson"] = geometry
        
        result.append(pattern_dict)
    
    return result

@router.get("/{pattern_id}", response_model=PatternDetailResponse)
def get_pattern(pattern_id: str, db: Session = Depends(get_db)):
    pattern = crud_pattern.get_by_id(db, pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern no encontrado")
    
    stops = crud_pattern.get_stops(db, pattern_id)
    stops_list = [
        {
            "id": s.id,
            "id_parada": s.id_parada,
            "sequence": s.sequence,
            "nombre_parada": s.nombre_parada,
            "latitud": float(s.latitud) if s.latitud else None,
            "longitud": float(s.longitud) if s.longitud else None
        }
        for s in stops
    ]
    
    geometry = crud_pattern.get_geometry_geojson(db, pattern_id)
    stats = crud_pattern.get_stats(db, pattern_id)
    
    return {
        "id": pattern.id,
        "name": pattern.name,
        "code": pattern.code,
        "sentido": pattern.sentido,
        "id_linea": pattern.id_linea,
        "nombre_linea": pattern.linea.nombre if pattern.linea else None,
        "short_name_linea": pattern.linea.short_name if pattern.linea else None,
        "geometry_geojson": geometry,
        "stops": stops_list,
        "total_stops": stats.get("total_stops", 0),
        "route_length_km": stats.get("route_length_km")
    }

@router.get("/line/{id_linea}", response_model=List[PatternResponse])
def get_patterns_by_line(id_linea: int, db: Session = Depends(get_db)):
    patterns = crud_pattern.get_by_line(db, id_linea)
    
    if not patterns:
        raise HTTPException(status_code=404, detail=f"No patterns para línea {id_linea}")
    
    result = []
    for pattern in patterns:
        geometry = crud_pattern.get_geometry_geojson(db, pattern.id)
        result.append({
            "id": pattern.id,
            "name": pattern.name,
            "code": pattern.code,
            "sentido": pattern.sentido,
            "id_linea": pattern.id_linea,
            "nombre_linea": pattern.linea.nombre if pattern.linea else None,
            "short_name_linea": pattern.linea.short_name if pattern.linea else None,
            "geometry_geojson": geometry
        })
    
    return result

@router.post("/", response_model=PatternResponse, status_code=status.HTTP_201_CREATED)
def create_pattern(pattern: PatternCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    from app.crud.line import crud_line
    line = crud_line.get_by_id(db, pattern.id_linea)
    if not line:
        raise HTTPException(status_code=404, detail=f"Línea {pattern.id_linea} no encontrada")
    
    db_pattern = crud_pattern.create(db, pattern)
    
    return {
        "id": db_pattern.id,
        "name": db_pattern.name,
        "code": db_pattern.code,
        "sentido": db_pattern.sentido,
        "id_linea": db_pattern.id_linea,
        "nombre_linea": line.nombre,
        "short_name_linea": line.short_name
    }

@router.put("/{pattern_id}", response_model=PatternResponse)
def update_pattern(pattern_id: str, pattern: PatternUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    db_pattern = crud_pattern.get_by_id(db, pattern_id)
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern no encontrado")
    
    updated_pattern = crud_pattern.update(db, db_pattern, pattern)
    
    return {
        "id": updated_pattern.id,
        "name": updated_pattern.name,
        "code": updated_pattern.code,
        "sentido": updated_pattern.sentido,
        "id_linea": updated_pattern.id_linea,
        "nombre_linea": updated_pattern.linea.nombre if updated_pattern.linea else None,
        "short_name_linea": updated_pattern.linea.short_name if updated_pattern.linea else None
    }

@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pattern(pattern_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    db_pattern = crud_pattern.get_by_id(db, pattern_id)
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern no encontrado")
    
    crud_pattern.delete(db, db_pattern)

@router.post("/{pattern_id}/stops", response_model=List[PatternStopResponse])
def assign_stops_to_pattern(pattern_id: str, stops: List[PatternStopCreate], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    db_pattern = crud_pattern.get_by_id(db, pattern_id)
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern no encontrado")
    
    sequences = [s.sequence for s in stops]
    if len(sequences) != len(set(sequences)):
        raise HTTPException(status_code=400, detail="Secuencias deben ser únicas")
    
    crud_pattern.add_stops(db, pattern_id, stops)
    updated_stops = crud_pattern.get_stops(db, pattern_id)
    
    return [
        {
            "id": s.id,
            "id_parada": s.id_parada,
            "sequence": s.sequence,
            "nombre_parada": s.nombre_parada,
            "latitud": float(s.latitud) if s.latitud else None,
            "longitud": float(s.longitud) if s.longitud else None
        }
        for s in updated_stops
    ]

@router.get("/{pattern_id}/stops", response_model=List[PatternStopResponse])
def get_pattern_stops(pattern_id: str, db: Session = Depends(get_db)):
    db_pattern = crud_pattern.get_by_id(db, pattern_id)
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern no encontrado")
    
    stops = crud_pattern.get_stops(db, pattern_id)
    
    return [
        {
            "id": s.id,
            "id_parada": s.id_parada,
            "sequence": s.sequence,
            "nombre_parada": s.nombre_parada,
            "latitud": float(s.latitud) if s.latitud else None,
            "longitud": float(s.longitud) if s.longitud else None
        }
        for s in stops
    ]

@router.get("/{pattern_id}/geometry")
def get_pattern_geometry(pattern_id: str, db: Session = Depends(get_db)):
    db_pattern = crud_pattern.get_by_id(db, pattern_id)
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern no encontrado")
    
    geometry = crud_pattern.get_geometry_geojson(db, pattern_id)
    
    if not geometry:
        raise HTTPException(status_code=404, detail="Sin geometría definida")
    
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "id": pattern_id,
            "name": db_pattern.name,
            "sentido": db_pattern.sentido
        }
    }
