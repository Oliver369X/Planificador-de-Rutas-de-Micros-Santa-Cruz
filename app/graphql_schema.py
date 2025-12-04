"""
GraphQL Schema para trufi-core
Implementa queries: patterns, pattern(id)
"""
import strawberry
from typing import List, Optional
from sqlalchemy import text
from app.database import SessionLocal

@strawberry.type
class Route:
    long_name: Optional[str] = strawberry.field(name="longName")
    short_name: Optional[str] = strawberry.field(name="shortName")
    color: Optional[str]
    mode: Optional[str]
    text_color: Optional[str] = strawberry.field(name="textColor")

@strawberry.type
class GeometryPoint:
    lat: float
    lon: float

@strawberry.type
class Stop:
    name: str
    lat: float
    lon: float

@strawberry.type
class Pattern:
    id: str
    name: str
    code: Optional[str]
    route: Optional[Route]
    geometry: Optional[List[GeometryPoint]] = None
    stops: Optional[List[Stop]] = None

def get_all_patterns() -> List[Pattern]:
    db = SessionLocal()
    try:
        # Usar COALESCE para manejar valores nulos y usar 'nombre' como fallback
        query = text("""
            SELECT 
                p.id,
                p.name,
                p.code,
                COALESCE(l.long_name, l.nombre) as long_name,
                COALESCE(l.short_name, l.nombre) as short_name,
                COALESCE(l.color, '0088FF') as color,
                COALESCE(l.mode, 'BUS') as mode,
                COALESCE(l.text_color, 'FFFFFF') as text_color
            FROM transporte.patterns p
            JOIN transporte.lineas l ON p.id_linea = l.id_linea
        """)
        results = db.execute(query).fetchall()
        
        patterns = []
        for r in results:
            patterns.append(Pattern(
                id=str(r.id),
                name=r.name or "",
                code=r.code or str(r.id),
                route=Route(
                    long_name=r.long_name or "",
                    short_name=r.short_name or "",
                    color=r.color or "0088FF",
                    mode=r.mode or "BUS",
                    text_color=r.text_color or "FFFFFF"
                )
            ))
        return patterns
    except Exception as e:
        print(f"Error in get_all_patterns: {e}")
        return []
    finally:
        db.close()

def get_pattern_detail(pattern_id: str) -> Optional[Pattern]:
    db = SessionLocal()
    try:
        geometry = []
        stops = []
        actual_pattern_id = pattern_id
        
        print(f"GraphQL get_pattern_detail called with: '{pattern_id}'")
        
        # trufi-core puede enviar solo el ID numérico (ej: "14") o el ID completo ("pattern:14:ida")
        # Si es solo un número, buscar el pattern usando el NOMBRE de la línea (número de ruta real)
        if pattern_id.isdigit():
            print(f"  -> Is digit, searching by linea.nombre (route number)...")
            # IMPORTANTE: Buscar por linea.nombre, NO por id_linea
            # porque id_linea=14 puede tener nombre="19", pero el usuario quiere la ruta "14"
            linea_query = text("""
                SELECT p.id FROM transporte.patterns p
                JOIN transporte.lineas l ON p.id_linea = l.id_linea
                WHERE l.nombre = :route_number
                ORDER BY p.id LIMIT 1
            """)
            linea_result = db.execute(linea_query, {"route_number": pattern_id}).fetchone()
            print(f"  -> Query result: {linea_result}")
            if linea_result:
                actual_pattern_id = linea_result[0]
                print(f"  -> Mapped to: {actual_pattern_id}")
        
        print(f"  -> Using actual_pattern_id: {actual_pattern_id}")

        
        # Get stops
        stops_query = text("""
            SELECT p.nombre_parada as name, p.latitud as lat, p.longitud as lon
            FROM transporte.pattern_stops ps
            JOIN transporte.paradas p ON ps.id_parada = p.id_parada
            WHERE ps.pattern_id = :id
            ORDER BY ps.sequence
        """)
        stops_results = db.execute(stops_query, {"id": actual_pattern_id}).fetchall()
        
        if stops_results:
            stops = [Stop(name=s.name or "", lat=float(s.lat), lon=float(s.lon)) for s in stops_results]
            # Usar las paradas como geometría (fallback si no hay LineString)
            geometry = [GeometryPoint(lat=float(s.lat), lon=float(s.lon)) for s in stops_results]
        
        # Intentar obtener geometría del patrón (LineString) si existe
        geom_query = text("""
            SELECT ST_Y(geom) as lat, ST_X(geom) as lon
            FROM (
                SELECT (ST_DumpPoints(geometry)).geom as geom
                FROM transporte.patterns
                WHERE id = :id AND geometry IS NOT NULL
            ) as points
        """)
        geom_results = db.execute(geom_query, {"id": actual_pattern_id}).fetchall()
        
        if geom_results:
            geometry = [GeometryPoint(lat=g.lat, lon=g.lon) for g in geom_results]
        
        # CRÍTICO: trufi-core llama .first en la lista, debe tener al menos 1 elemento
        # Si no hay geometría ni paradas, usar centro de Santa Cruz como fallback
        if not geometry:
            geometry = [GeometryPoint(lat=-17.7833, lon=-63.1821)]
        if not stops:
            stops = [Stop(name="Santa Cruz Centro", lat=-17.7833, lon=-63.1821)]
        
        return Pattern(
            id=pattern_id,
            name="",
            code=None,
            route=None,
            geometry=geometry,
            stops=stops
        )
    except Exception as e:
        print(f"Error in get_pattern_detail: {e}")
        # CRÍTICO: Nunca devolver listas vacías
        return Pattern(
            id=pattern_id,
            name="",
            code=None,
            route=None,
            geometry=[GeometryPoint(lat=-17.7833, lon=-63.1821)],
            stops=[Stop(name="Santa Cruz Centro", lat=-17.7833, lon=-63.1821)]

        )
    finally:
        db.close()

@strawberry.type
class Query:
    @strawberry.field
    def patterns(self) -> List[Pattern]:
        return get_all_patterns()
    
    @strawberry.field
    def pattern(self, id: str) -> Optional[Pattern]:
        return get_pattern_detail(id)

schema = strawberry.Schema(query=Query)
