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
        # Return empty plan on error to avoid crashing app
        from app.schemas.otp_schemas import PlanSchema
        return PlanResponse(plan=PlanSchema())
