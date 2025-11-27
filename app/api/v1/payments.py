from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.crud.payment import crud_payment
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payment: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # En un caso real, aquí iría la lógica de validación de pago o integración con pasarela
    return crud_payment.create(db, payment)
