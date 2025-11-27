from sqlalchemy.orm import Session
from typing import List
from app.models.line import Line
from app.schemas.line import LineCreate, LineUpdate

class CRUDLine:
    def get_all_active(self, db: Session) -> List[Line]:
        return db.query(Line).filter(Line.activa == True).all()
    
    def get_by_id(self, db: Session, line_id: int):
        return db.query(Line).filter(Line.id_linea == line_id).first()
    
    def create(self, db: Session, line: LineCreate):
        db_line = Line(**line.model_dump())
        db.add(db_line)
        db.commit()
        db.refresh(db_line)
        return db_line
    
    def update(self, db: Session, db_line: Line, line_update: LineUpdate):
        update_data = line_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_line, key, value)
        db.add(db_line)
        db.commit()
        db.refresh(db_line)
        return db_line
    
    def delete(self, db: Session, db_line: Line):
        db.delete(db_line)
        db.commit()

crud_line = CRUDLine()
