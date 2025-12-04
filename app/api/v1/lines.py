from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.line import LineCreate, LineResponse, LineUpdate
from app.crud.line import crud_line
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/lines", tags=["lines"])

@router.get("/", response_model=List[LineResponse])
def get_all_lines(db: Session = Depends(get_db)):
    return crud_line.get_all_active(db)

@router.get("/{id_linea}", response_model=LineResponse)
def get_line(id_linea: int, db: Session = Depends(get_db)):
    line = crud_line.get_by_id(db, id_linea)
    if not line:
        raise HTTPException(status_code=404, detail="Línea no encontrada")
    return line

@router.post("/", response_model=LineResponse, status_code=status.HTTP_201_CREATED)
def create_line(
    line: LineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    return crud_line.create(db, line)

@router.put("/{id_linea}", response_model=LineResponse)
def update_line(
    id_linea: int,
    line: LineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    existing_line = crud_line.get_by_id(db, id_linea)
    if not existing_line:
        raise HTTPException(status_code=404, detail="Línea no encontrada")
    
    return crud_line.update(db, existing_line, line)

@router.delete("/{id_linea}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line(
    id_linea: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    existing_line = crud_line.get_by_id(db, id_linea)
    if not existing_line:
        raise HTTPException(status_code=404, detail="Línea no encontrada")
    
    crud_line.delete(db, existing_line)

@router.get("/{id_linea}/route")
def get_line_route(id_linea: int, db: Session = Depends(get_db)):
    """
    Obtiene la geometría de la ruta (patterns) en formato GeoJSON.
    """
    from sqlalchemy import text
    import json
    
    query = text("""
        SELECT 
            id,
            name,
            sentido,
            ST_AsGeoJSON(geometry)::json as geometry
        FROM transporte.patterns
        WHERE id_linea = :id_linea
    """)
    
    patterns = db.execute(query, {"id_linea": id_linea}).fetchall()
    
    if not patterns:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    
    features = []
    for p in patterns:
        features.append({
            "type": "Feature",
            "geometry": p.geometry,
            "properties": {
                "id": p.id,
                "name": p.name,
                "sentido": p.sentido
            }
        })
        
    return {"type": "FeatureCollection", "features": features}
