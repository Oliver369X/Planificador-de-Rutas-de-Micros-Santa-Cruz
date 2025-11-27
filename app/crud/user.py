from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import AuthService

class CRUDUser:
    def get_by_email(self, db: Session, email: str):
        return db.query(User).filter(User.correo == email).first()
    
    def get(self, db: Session, user_id: int):
        return db.query(User).filter(User.id_usuario == user_id).first()
    
    def create(self, db: Session, user: UserCreate):
        hashed_password = AuthService.hash_password(user.contraseña)
        db_user = User(
            nombre=user.nombre,
            correo=user.correo,
            contraseña=hashed_password,
            rol=user.rol
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

crud_user = CRUDUser()
