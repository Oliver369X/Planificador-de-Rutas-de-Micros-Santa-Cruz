from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats")
def get_system_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    lineas_stats = db.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN activa = true THEN 1 ELSE 0 END) as activas
        FROM transporte.lineas
    """)).fetchone()
    
    paradas_stats = db.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN activa = true THEN 1 ELSE 0 END) as activas
        FROM transporte.paradas
    """)).fetchone()
    
    patterns_stats = db.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN geometry IS NOT NULL THEN 1 ELSE 0 END) as con_geometria,
            SUM(ST_Length(geometry::geography)) / 1000 as longitud_total_km
        FROM transporte.patterns
    """)).fetchone()
    
    cobertura = db.execute(text("""
        SELECT 
            ST_Area(ST_ConvexHull(ST_Collect(geom))::geography) / 1000000 as area_km2
        FROM transporte.paradas
        WHERE activa = true
    """)).fetchone()
    
    return {
        "lineas": {
            "total": lineas_stats.total or 0,
            "activas": lineas_stats.activas or 0
        },
        "paradas": {
            "total": paradas_stats.total or 0,
            "activas": paradas_stats.activas or 0
        },
        "patterns": {
            "total": patterns_stats.total or 0,
            "con_geometria": patterns_stats.con_geometria or 0
        },
        "red_transporte": {
            "longitud_total_km": round(patterns_stats.longitud_total_km, 2) if patterns_stats.longitud_total_km else 0,
            "area_cobertura_km2": round(cobertura.area_km2, 2) if cobertura.area_km2 else 0
        }
    }

@router.get("/health")
def system_health_check(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "Administrador":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    issues = []
    warnings = []
    
    lineas_sin_patterns = db.execute(text("""
        SELECT l.id_linea, l.nombre
        FROM transporte.lineas l
        LEFT JOIN transporte.patterns p ON l.id_linea = p.id_linea
        WHERE l.activa = true AND p.id IS NULL
    """)).fetchall()
    
    if lineas_sin_patterns:
        issues.append({
            "type": "lineas_sin_patterns",
            "severity": "high",
            "count": len(lineas_sin_patterns),
            "message": f"{len(lineas_sin_patterns)} líneas activas sin patterns"
        })
    
    patterns_sin_geom = db.execute(text("""
        SELECT p.id, p.name
        FROM transporte.patterns p
        WHERE p.geometry IS NULL
    """)).fetchall()
    
    if patterns_sin_geom:
        warnings.append({
            "type": "patterns_sin_geometria",
            "severity": "medium",
            "count": len(patterns_sin_geom),
            "message": f"{len(patterns_sin_geom)} patterns sin geometría"
        })
    
    if issues:
        status = "unhealthy"
    elif warnings:
        status = "warning"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "timestamp": db.execute(text("SELECT NOW()")).scalar(),
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "critical_issues": len(issues),
            "warnings": len(warnings)
        }
    }
