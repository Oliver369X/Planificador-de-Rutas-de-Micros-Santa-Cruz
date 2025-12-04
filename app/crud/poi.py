from sqlalchemy.orm import Session
from app.models.poi import PointOfInterest
from app.schemas.poi import POICreate, POIUpdate
from typing import List, Optional

class CRUDPOI:
    def get_by_id(self, db: Session, id: int):
        return db.query(PointOfInterest).filter(PointOfInterest.id == id).first()

    def create(self, db: Session, obj_in: POICreate):
        db_obj = PointOfInterest(
            nombre=obj_in.nombre,
            tipo=obj_in.tipo,
            subtipo=obj_in.subtipo,
            latitud=obj_in.latitud,
            longitud=obj_in.longitud,
            direccion=obj_in.direccion,
            telefono=obj_in.telefono,
            horario=obj_in.horario,
            distrito=obj_in.distrito,
            poi_metadata=obj_in.poi_metadata
        )
        # Generar objectid si es necesario (o dejar null)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: PointOfInterest, obj_in: POIUpdate):
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: PointOfInterest):
        db.delete(db_obj)
        db.commit()

crud_poi = CRUDPOI()
