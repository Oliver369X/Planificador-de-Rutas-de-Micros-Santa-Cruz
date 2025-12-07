from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from app.models.pattern import Pattern
from app.models.pattern_stop import PatternStop
from app.schemas.pattern import PatternCreate, PatternUpdate, PatternStopCreate

class CRUDPattern:
    
    def get_by_id(self, db: Session, pattern_id: str) -> Optional[Pattern]:
        return db.query(Pattern).filter(Pattern.id == pattern_id).first()
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[Pattern]:
        return db.query(Pattern).offset(skip).limit(limit).all()
    
    def get_by_line(self, db: Session, id_linea: int) -> List[Pattern]:
        return db.query(Pattern).filter(Pattern.id_linea == id_linea).all()
    
    def create(self, db: Session, pattern: PatternCreate) -> Pattern:
        pattern_id = f"pattern:{pattern.id_linea}:{pattern.sentido}"
        
        existing = self.get_by_id(db, pattern_id)
        if existing:
            counter = 1
            while existing:
                pattern_id = f"pattern:{pattern.id_linea}:{pattern.sentido}:{counter}"
                existing = self.get_by_id(db, pattern_id)
                counter += 1
        
        geometry_wkt = None
        if pattern.geometry_geojson:
            try:
                coords = pattern.geometry_geojson.get('coordinates', [])
                if coords:
                    points = ', '.join([f"{lon} {lat}" for lon, lat in coords])
                    geometry_wkt = f"LINESTRING({points})"
            except:
                pass
        
        db_pattern = Pattern(
            id=pattern_id,
            code=pattern.code or str(pattern.id_linea),
            name=pattern.name,
            id_linea=pattern.id_linea,
            sentido=pattern.sentido
        )
        
        if geometry_wkt:
            query = text("""
                UPDATE transporte.patterns 
                SET geometry = ST_GeomFromText(:wkt, 4326)
                WHERE id = :pattern_id
            """)
            db.execute(query, {"wkt": geometry_wkt, "pattern_id": pattern_id})
        
        db.add(db_pattern)
        db.commit()
        db.refresh(db_pattern)
        
        return db_pattern
    
    def update(self, db: Session, db_pattern: Pattern, pattern: PatternUpdate) -> Pattern:
        update_data = pattern.model_dump(exclude_unset=True)
        
        if 'geometry_geojson' in update_data:
            geometry_geojson = update_data.pop('geometry_geojson')
            if geometry_geojson:
                try:
                    coords = geometry_geojson.get('coordinates', [])
                    if coords:
                        points = ', '.join([f"{lon} {lat}" for lon, lat in coords])
                        geometry_wkt = f"LINESTRING({points})"
                        
                        query = text("""
                            UPDATE transporte.patterns 
                            SET geometry = ST_GeomFromText(:wkt, 4326)
                            WHERE id = :pattern_id
                        """)
                        db.execute(query, {"wkt": geometry_wkt, "pattern_id": db_pattern.id})
                except:
                    pass
        
        for field, value in update_data.items():
            setattr(db_pattern, field, value)
        
        db.commit()
        db.refresh(db_pattern)
        return db_pattern
    
    def delete(self, db: Session, db_pattern: Pattern) -> None:
        db.delete(db_pattern)
        db.commit()
    
    def add_stops(self, db: Session, pattern_id: str, stops: List[PatternStopCreate]) -> List[PatternStop]:
        db.query(PatternStop).filter(PatternStop.pattern_id == pattern_id).delete()
        
        db_stops = []
        for stop in stops:
            db_stop = PatternStop(
                pattern_id=pattern_id,
                id_parada=stop.id_parada,
                sequence=stop.sequence
            )
            db.add(db_stop)
            db_stops.append(db_stop)
        
        db.commit()
        return db_stops
    
    def get_stops(self, db: Session, pattern_id: str):
        query = text("""
            SELECT 
                ps.id,
                ps.id_parada,
                ps.sequence,
                p.nombre_parada,
                p.latitud,
                p.longitud
            FROM transporte.pattern_stops ps
            JOIN transporte.paradas p ON ps.id_parada = p.id_parada
            WHERE ps.pattern_id = :pattern_id
            ORDER BY ps.sequence ASC
        """)
        
        return db.execute(query, {"pattern_id": pattern_id}).fetchall()
    
    def get_geometry_geojson(self, db: Session, pattern_id: str) -> Optional[dict]:
        query = text("""
            SELECT ST_AsGeoJSON(geometry)::json as geojson
            FROM transporte.patterns
            WHERE id = :pattern_id
        """)
        
        result = db.execute(query, {"pattern_id": pattern_id}).fetchone()
        if result and result.geojson:
            return result.geojson
        return None
    
    def get_stats(self, db: Session, pattern_id: str) -> dict:
        query = text("""
            SELECT 
                COUNT(ps.id) as total_stops,
                ST_Length(p.geometry::geography) / 1000 as route_length_km
            FROM transporte.patterns p
            LEFT JOIN transporte.pattern_stops ps ON p.id = ps.pattern_id
            WHERE p.id = :pattern_id
            GROUP BY p.id, p.geometry
        """)
        
        result = db.execute(query, {"pattern_id": pattern_id}).fetchone()
        if result:
            return {
                "total_stops": result.total_stops or 0,
                "route_length_km": round(result.route_length_km, 2) if result.route_length_km else None
            }
        return {"total_stops": 0, "route_length_km": None}

crud_pattern = CRUDPattern()
