from sqlalchemy.orm import Session
from typing import List
from app.models.route import Route
from app.schemas.route import RouteCreate, RouteUpdate

class CRUDRoute:
    def get_by_line(self, db: Session, line_id: int) -> List[Route]:
        return db.query(Route).filter(Route.id_linea == line_id).order_by(Route.orden).all()
    
    def create(self, db: Session, route: RouteCreate):
        db_route = Route(**route.model_dump())
        db.add(db_route)
        db.commit()
        db.refresh(db_route)
        return db_route

crud_route = CRUDRoute()
