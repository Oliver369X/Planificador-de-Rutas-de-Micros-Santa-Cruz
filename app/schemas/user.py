from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: str = "Usuario"

class UserCreate(UserBase):
    contraseña: str

class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    saldo: Optional[int] = None

class UserResponse(UserBase):
    id_usuario: int
    saldo: int
    activo: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True
