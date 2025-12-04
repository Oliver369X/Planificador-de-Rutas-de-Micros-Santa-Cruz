from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.crud.favorite import crud_favorite
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/favorites", tags=["favorites"])

@router.get("/", response_model=List[FavoriteResponse])
def get_my_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene los favoritos del usuario actual"""
    return crud_favorite.get_by_user(db, user_id=current_user.id_usuario)

@router.post("/", response_model=FavoriteResponse)
def create_favorite(
    favorite: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea un nuevo favorito"""
    return crud_favorite.create(db, favorite, user_id=current_user.id_usuario)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Elimina un favorito"""
    deleted = crud_favorite.delete(db, id, user_id=current_user.id_usuario)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorito no encontrado")
