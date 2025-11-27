from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.crud.user import crud_user
from app.services.auth_service import AuthService
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    correo: str
    contraseña: str

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud_user.get_by_email(db, user.correo)
    if db_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    return crud_user.create(db, user)

@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = crud_user.get_by_email(db, credentials.correo)
    if not user or not AuthService.verify_password(credentials.contraseña, user.contraseña):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    access_token = AuthService.create_access_token({"sub": str(user.id_usuario)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}
