from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.route import RouteCreate, RouteResponse
from app.crud.route import crud_route
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/routes", tags=["routes"])

@router.get("/line/{line_id}", response_model=List[RouteResponse])
def get_routes_by_line(line_id: int, db: Session = Depends(get_db)):
    return crud_route.get_by_line(db, line_id)

@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    route: RouteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    return crud_route.create(db, route)
