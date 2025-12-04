from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.stop import StopCreate, StopResponse, StopUpdate
from app.crud.stop import crud_stop
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/stops", tags=["stops"])

@router.get("/", response_model=List[StopResponse])
def get_all_stops(db: Session = Depends(get_db)):
    return crud_stop.get_all_active(db)

@router.get("/{id_parada}", response_model=StopResponse)
def get_stop(id_parada: int, db: Session = Depends(get_db)):
    stop = crud_stop.get_by_id(db, id_parada)
    if not stop:
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    return stop

@router.post("/", response_model=StopResponse, status_code=status.HTTP_201_CREATED)
def create_stop(
    stop: StopCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    return crud_stop.create(db, stop)

@router.put("/{id_parada}", response_model=StopResponse)
def update_stop(
    id_parada: int,
    stop: StopUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    existing_stop = crud_stop.get_by_id(db, id_parada)
    if not existing_stop:
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    
    return crud_stop.update(db, existing_stop, stop)

@router.get("/nearby/", response_model=List[StopResponse])
def get_nearby_stops(
    lat: float,
    lon: float,
    radius: float = 500.0,
    db: Session = Depends(get_db)
):
    """
    Get stops within a radius (in meters) of a location.
    """
    return crud_stop.get_nearby(db, lat, lon, radius)

@router.delete("/{id_parada}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stop(
    id_parada: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    existing_stop = crud_stop.get_by_id(db, id_parada)
    if not existing_stop:
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    
    crud_stop.delete(db, existing_stop)
