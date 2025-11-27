from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate

class CRUDPayment:
    def create(self, db: Session, payment: PaymentCreate):
        db_payment = Payment(**payment.model_dump())
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment

crud_payment = CRUDPayment()
