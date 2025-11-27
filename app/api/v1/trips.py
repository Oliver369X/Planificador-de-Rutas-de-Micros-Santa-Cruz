from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.trip import TripRequest, TripResponse
from app.models import User, Trip
from app.dependencies import get_current_user
from app.services.trip_planner import TripPlanner
from app.crud.trip import crud_trip

router = APIRouter(prefix="/trips", tags=["trips"])

@router.post("/plan", status_code=200)
def plan_trip(
    trip_request: TripRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Planifica un viaje desde origen a destino."""
    plan = TripPlanner.plan_trip(
        db,
        current_user.id_usuario,
        trip_request.origen_lat,
        trip_request.origen_lon,
        trip_request.destino_lat,
        trip_request.destino_lon
    )
    
    if "error" in plan:
        raise HTTPException(status_code=404, detail=plan["error"])
    
    return plan

@router.post("/save", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def save_trip(
    trip_request: TripRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Guarda un viaje en el historial del usuario."""
    plan = TripPlanner.plan_trip(
        db,
        current_user.id_usuario,
        trip_request.origen_lat,
        trip_request.origen_lon,
        trip_request.destino_lat,
        trip_request.destino_lon
    )
    
    if "error" in plan:
        raise HTTPException(status_code=404, detail=plan["error"])
    
    # Guardar viaje
    trip_data = {
        "id_usuario": current_user.id_usuario,
        "origen_lat": trip_request.origen_lat,
        "origen_lon": trip_request.origen_lon,
        "destino_lat": trip_request.destino_lat,
        "destino_lon": trip_request.destino_lon,
        "tiempo_estimado_total": plan["alternativas"][0]["tiempo_estimado"] if plan["alternativas"] else None,
        "distancia_total": plan["alternativas"][0]["distancia"] if plan["alternativas"] else None
    }
    
    return crud_trip.create(db, trip_data)

@router.get("/history", status_code=200)
def get_trip_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Obtiene el historial de viajes del usuario."""
    trips = db.query(Trip).filter(
        Trip.id_usuario == current_user.id_usuario
    ).order_by(Trip.fecha_hora.desc()).limit(limit).all()
    
    return trips
