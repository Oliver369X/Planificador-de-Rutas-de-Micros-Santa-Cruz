from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services.route_planner import route_planner
from app.schemas.otp_schemas import PlanResponse

router = APIRouter(tags=["OTP Compatible"])

@router.get("/plan", response_model=PlanResponse)
def plan_route(
    fromPlace: str = Query(..., description="Origin coordinates: lat,lon"),
    toPlace: str = Query(..., description="Destination coordinates: lat,lon"),
    date: str = Query(default="today", description="Date MM-DD-YYYY"),
    time: str = Query(default="12:00:00", description="Time HH:mm:ss"),
    numItineraries: int = Query(default=5, description="Number of itineraries"),
    maxWalkDistance: float = Query(default=1500.0, description="Max walk distance in meters"),
    mode: str = Query(default="WALK,BUS", description="Transport modes"),
    db: Session = Depends(get_db)
):
    """
    OTP-compatible route planning endpoint.
    Example: /api/v1/plan?fromPlace=-17.7833,-63.1821&toPlace=-17.7512,-63.1755
    """
    try:
        # Parse coordinates
        from_lat, from_lon = map(float, fromPlace.split(','))
        to_lat, to_lon = map(float, toPlace.split(','))
        
        # Call planner service
        plan = route_planner.plan_route(
            db=db,
            from_lat=from_lat,
            from_lon=from_lon,
            to_lat=to_lat,
            to_lon=to_lon,
            max_walk_distance=maxWalkDistance,
            num_itineraries=numItineraries
        )
        
        return PlanResponse(plan=plan)
    except Exception as e:
        print(f"Error planning route: {e}")
        # FALLBACK DE EMERGENCIA: devolver ruta caminando en línea recta
        # Esto evita que la app crashee con "Valid value range is empty"
        try:
             # Generar timestamp actual
            import time
            current_time = int(time.time() * 1000)
            
            # Obtener coords de los params (suponiendo que son válidos por venir de query)
            from_lat, from_lon = map(float, fromPlace.split(','))
            to_lat, to_lon = map(float, toPlace.split(','))
            
            # Usar el planner para generar solo la caminata
            fallback_plan = route_planner._build_walk_only_itinerary(
                from_lat, from_lon, to_lat, to_lon, current_time
            )
            
            # Construir respuesta válida con 1 itinerario
            from app.schemas.otp_schemas import PlaceSchema, PlanSchema
            emergency_plan = PlanSchema(
                itineraries=[fallback_plan],
                date=current_time,
                from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
                to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination")
            )
            return PlanResponse(plan=emergency_plan)
            
        except Exception as fallback_error:
            print(f"Emergency fallback failed: {fallback_error}")
            # Si hasta el fallback falla, recién devolvemos vacío (last resort)
            from app.schemas.otp_schemas import PlanSchema
            return PlanResponse(plan=PlanSchema())
