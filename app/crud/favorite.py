from sqlalchemy.orm import Session
from app.models.favorite import Favorite
from app.schemas.favorite import FavoriteCreate, FavoriteUpdate

class CRUDFavorite:
    def get_by_user(self, db: Session, user_id: int):
        return db.query(Favorite).filter(Favorite.id_usuario == user_id).all()

    def create(self, db: Session, obj_in: FavoriteCreate, user_id: int):
        db_obj = Favorite(**obj_in.dict(), id_usuario=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int, user_id: int):
        obj = db.query(Favorite).filter(Favorite.id == id, Favorite.id_usuario == user_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

crud_favorite = CRUDFavorite()
