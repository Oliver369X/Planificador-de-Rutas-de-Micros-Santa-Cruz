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
        # Mapear 'nombre' del schema a 'nombre_parada' del modelo
        stop_data = stop.model_dump()
        if 'nombre' in stop_data:
            stop_data['nombre_parada'] = stop_data.pop('nombre')
            
        db_stop = Stop(**stop_data)
        db.add(db_stop)
        db.commit()
        db.refresh(db_stop)
        return db_stop
    
    def update(self, db: Session, db_stop: Stop, stop_update: StopUpdate):
        update_data = stop_update.model_dump(exclude_unset=True)
        # Mapear 'nombre' a 'nombre_parada'
        if 'nombre' in update_data:
            update_data['nombre_parada'] = update_data.pop('nombre')
            
        for key, value in update_data.items():
            setattr(db_stop, key, value)
        db.add(db_stop)
        db.commit()
        db.refresh(db_stop)
        return db_stop

    def get_nearby(self, db: Session, lat: float, lon: float, radius: float) -> List[Stop]:
        # radius in meters. ST_DWithin takes degrees if SRID is 4326, so we need to cast to geography or use appropriate SRID.
        # Assuming data is stored as Geometry(Point, 4326).
        # Casting to geography allows using meters for distance.
        from geoalchemy2.functions import ST_DWithin, ST_MakePoint
        from sqlalchemy import func
        
        # Create a point from input lat/lon
        point = ST_MakePoint(lon, lat)
        
        # Use ST_DWithin with geography cast for meters distance
        # Note: This assumes the 'geom' column exists and is populated.
        # If 'geom' is not yet populated in the DB, this will return empty or fail.
        # We need to ensure 'geom' is defined in the model.
        return db.query(Stop).filter(
            ST_DWithin(
                Stop.geom.cast(func.geography),
                func.ST_SetSRID(point, 4326).cast(func.geography),
                radius
            )
        ).all()

    def delete(self, db: Session, db_stop: Stop):
        db.delete(db_stop)
        db.commit()

crud_stop = CRUDStop()
