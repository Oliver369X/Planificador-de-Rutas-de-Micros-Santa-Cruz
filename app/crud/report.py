from sqlalchemy.orm import Session
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate
from typing import Optional

class CRUDReport:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Report).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ReportCreate, user_id: Optional[int] = None):
        db_obj = Report(**obj_in.dict(), id_usuario=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_status(self, db: Session, id: int, resuelto: bool):
        obj = db.query(Report).filter(Report.id == id).first()
        if obj:
            obj.resuelto = resuelto
            db.commit()
            db.refresh(obj)
        return obj

crud_report = CRUDReport()
