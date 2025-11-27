from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.transfer import TransferCreate, TransferResponse
from app.crud.transfer import crud_transfer
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/transfers", tags=["transfers"])

@router.post("/", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    transfer: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    return crud_transfer.create(db, transfer)
