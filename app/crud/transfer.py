from sqlalchemy.orm import Session
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreate

class CRUDTransfer:
    def create(self, db: Session, transfer: TransferCreate):
        db_transfer = Transfer(**transfer.model_dump())
        db.add(db_transfer)
        db.commit()
        db.refresh(db_transfer)
        return db_transfer

crud_transfer = CRUDTransfer()
