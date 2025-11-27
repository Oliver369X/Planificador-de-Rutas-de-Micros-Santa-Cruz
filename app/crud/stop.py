from sqlalchemy.orm import Session
from typing import List
from app.models.stop import Stop
from app.schemas.stop import StopCreate, StopUpdate

class CRUDStop:
    def get_all_active(self, db: Session) -> List[Stop]:
        return db.query(Stop).filter(Stop.activa == True).all()
    
    def get_by_id(self, db: Session, stop_id: int):
        return db.query(Stop).filter(Stop.id_parada == stop_id).first()
    
    def create(self, db: Session, stop: StopCreate):
        db_stop = Stop(**stop.model_dump())
        # PostGIS geometry handling could be added here if needed, 
        # but for now we trust lat/lon are enough or trigger handles it.
        # Ideally we set geom from lat/lon:
        # db_stop.geom = f'POINT({stop.longitud} {stop.latitud})'
        db.add(db_stop)
        db.commit()
        db.refresh(db_stop)
        return db_stop
    
    def update(self, db: Session, db_stop: Stop, stop_update: StopUpdate):
        update_data = stop_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_stop, key, value)
        db.add(db_stop)
        db.commit()
        db.refresh(db_stop)
        return db_stop

crud_stop = CRUDStop()
