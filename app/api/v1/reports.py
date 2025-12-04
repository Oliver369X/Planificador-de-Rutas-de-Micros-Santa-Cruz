from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.report import ReportCreate, ReportResponse, ReportUpdate
from app.crud.report import crud_report
from app.models import User
from app.dependencies import get_current_user
from typing import Optional

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/", response_model=ReportResponse)
def create_report(
    report: ReportCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) # Opcional si permitimos anónimos, pero get_current_user fuerza auth.
):
    """Crea un reporte (requiere auth por ahora)"""
    # Si queremos permitir anónimos, tendríamos que cambiar la dependencia.
    # Por ahora asumimos que solo usuarios logueados reportan.
    return crud_report.create(db, report, user_id=current_user.id_usuario)

@router.get("/", response_model=List[ReportResponse])
def get_reports(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista reportes (Solo Admin)"""
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    return crud_report.get_all(db, skip, limit)

@router.put("/{id}/resolve", response_model=ReportResponse)
def resolve_report(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marca un reporte como resuelto (Solo Admin)"""
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    report = crud_report.update_status(db, id, resuelto=True)
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return report
