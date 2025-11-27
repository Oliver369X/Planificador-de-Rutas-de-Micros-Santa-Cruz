from sqlalchemy.orm import Session
from app.models.trip import Trip

class CRUDTrip:
    def create(self, db: Session, trip_data: dict):
        db_trip = Trip(**trip_data)
        db.add(db_trip)
        db.commit()
        db.refresh(db_trip)
        return db_trip

crud_trip = CRUDTrip()
