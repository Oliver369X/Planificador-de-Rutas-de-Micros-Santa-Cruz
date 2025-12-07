"""
Planificador de rutas mejorado con soporte para transbordos.
Características:
- Rutas directas (1 micro)
- Rutas con 1 transbordo (2 micros)
- Cálculo de tiempos realistas
- Ordenamiento por tiempo total
"""
import time
import math
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.otp_schemas import (
    PlanSchema, ItinerarySchema, LegSchema, PlaceSchema, LegGeometry
)

# Constantes de velocidad (metros por minuto)
WALK_SPEED = 80  # ~5 km/h
BUS_SPEED = 333  # ~20 km/h (promedio considerando paradas y tráfico)

# Tiempos fijos
WAIT_TIME_MINUTES = 5  # Tiempo promedio de espera en parada
TRANSFER_TIME_MINUTES = 3  # Tiempo adicional para transbordo

def encode_polyline(coordinates: List[Tuple[float, float]]) -> str:
    """Codifica coordenadas en formato polyline de Google"""
    if not coordinates:
        return ""
    
    encoded = []
    prev_lat = 0
    prev_lon = 0
    
    for lat, lon in coordinates:
        lat_e5 = int(round(lat * 1e5))
        lon_e5 = int(round(lon * 1e5))
        
        d_lat = lat_e5 - prev_lat
        d_lon = lon_e5 - prev_lon
        
        prev_lat = lat_e5
        prev_lon = lon_e5
        
        for val in [d_lat, d_lon]:
            val = ~(val << 1) if val < 0 else (val << 1)
            while val >= 0x20:
                encoded.append(chr((0x20 | (val & 0x1f)) + 63))
                val >>= 5
            encoded.append(chr(val + 63))
    
    return ''.join(encoded)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia en metros entre dos coordenadas"""
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


class RoutePlanner:
    """Planificador de rutas con soporte para transbordos"""
    
    def plan_route(
        self,
        db: Session,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        max_walk_distance: float = 1500.0,
        num_itineraries: int = 5
    ) -> PlanSchema:
        """
        Planifica ruta buscando la forma más rápida de llegar.
        1. Busca rutas directas (1 micro)
        2. Si no hay suficientes, busca rutas con 1 transbordo (2 micros)
        3. Ordena por tiempo total y devuelve las mejores
        """
        current_time = int(time.time() * 1000)
        itineraries = []
        
        # Calcular distancia directa para ajustar el radio de búsqueda
        direct_distance = haversine_distance(from_lat, from_lon, to_lat, to_lon)
        
        # Radio de búsqueda basado en distancia del viaje
        if direct_distance > 5000:  # > 5km
            geometry_radius = 400  # metros del trazado
            stop_radius = 2000
        elif direct_distance > 2000:  # > 2km
            geometry_radius = 350
            stop_radius = 1800
        else:
            geometry_radius = 300
            stop_radius = 1500
        
        # ===== MÉTODO 1: Buscar rutas por GEOMETRÍA (trazado de la ruta) =====
        # En Santa Cruz los micros paran en cualquier esquina
        print(f"[RoutePlanner] Searching by geometry (radius={geometry_radius}m)...")
        geometry_routes = self._find_routes_by_geometry(
            db, from_lat, from_lon, to_lat, to_lon, radius=geometry_radius
        )
        
        for route in geometry_routes[:15]:
            itinerary = self._build_geometry_itinerary(
                db, route, from_lat, from_lon, to_lat, to_lon, current_time
            )
            if itinerary:
                itineraries.append(itinerary)
        
        print(f"[RoutePlanner] Itineraries from geometry: {len(itineraries)}")
        
        # ===== MÉTODO 2: Buscar por paradas (método tradicional) =====
        if len(itineraries) < num_itineraries:
            origin_stops = self._find_nearby_stops(db, from_lat, from_lon, radius=stop_radius, limit=50)
            dest_stops = self._find_nearby_stops(db, to_lat, to_lon, radius=stop_radius, limit=50)
            
            print(f"[RoutePlanner] Origin stops: {len(origin_stops)}, Dest stops: {len(dest_stops)}")
            
            direct_routes = self._find_direct_routes(db, origin_stops, dest_stops)
            print(f"[RoutePlanner] Direct routes found: {len(direct_routes)}")
            
            for route in direct_routes[:10]:
                itinerary = self._build_direct_itinerary(
                    db, route, from_lat, from_lon, to_lat, to_lon, current_time
                )
                if itinerary:
                    itineraries.append(itinerary)
        
        # ===== MÉTODO 3: Rutas con transbordo =====
        if len(itineraries) < num_itineraries:
            print("[RoutePlanner] Searching for transfer routes...")
            origin_stops = self._find_nearby_stops(db, from_lat, from_lon, radius=stop_radius, limit=50)
            dest_stops = self._find_nearby_stops(db, to_lat, to_lon, radius=stop_radius, limit=50)
            transfer_routes = self._find_transfer_routes(db, origin_stops, dest_stops)
            print(f"[RoutePlanner] Transfer routes found: {len(transfer_routes)}")
            
            for route in transfer_routes[:10]:
                itinerary = self._build_transfer_itinerary(
                    db, route, from_lat, from_lon, to_lat, to_lon, current_time
                )
                if itinerary:
                    itineraries.append(itinerary)
        
        # 3. Ordenar por duración total y tomar las mejores
        itineraries.sort(key=lambda x: x.duration)
        itineraries = itineraries[:num_itineraries]
        
        # 4. Si aún no hay itinerarios, agregar ruta a pie como fallback
        if not itineraries:
            print("[RoutePlanner] No transit routes, adding walk fallback")
            walk_itinerary = self._build_walk_only_itinerary(
                from_lat, from_lon, to_lat, to_lon, current_time
            )
            itineraries.append(walk_itinerary)
        
        print(f"[RoutePlanner] Final itineraries: {len(itineraries)}")
        
        return PlanSchema(
            itineraries=itineraries,
            date=current_time,
            from_=PlaceSchema(name="Origin", lat=from_lat, lon=from_lon),
            to=PlaceSchema(name="Destination", lat=to_lat, lon=to_lon)
        )

    def _find_nearby_stops(self, db: Session, lat: float, lon: float, radius: int = 1000, limit: int = 20):
        """Busca paradas cercanas usando PostGIS"""
        query = text("""
            SELECT id_parada, nombre_parada, latitud, longitud,
                   ST_Distance(
                       geom::geography, 
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   ) as distance
            FROM transporte.paradas
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY distance ASC
            LIMIT :limit
        """)
        return db.execute(query, {"lat": lat, "lon": lon, "radius": radius, "limit": limit}).fetchall()

    def _find_routes_by_geometry(self, db: Session, from_lat: float, from_lon: float, 
                                  to_lat: float, to_lon: float, radius: int = 300):
        """
        Encuentra rutas cuya GEOMETRÍA pase cerca del origen y destino.
        En Santa Cruz, los micros paran en cualquier esquina, así que buscamos
        rutas cuyo trazado pase cerca de ambos puntos.
        """
        query = text("""
            WITH routes_near_origin AS (
                -- Rutas que pasan cerca del origen
                SELECT DISTINCT p.id as pattern_id, 
                       p.id_linea,
                       ST_Distance(
                           p.geometry::geography,
                           ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography
                       ) as dist_from_origin
                FROM transporte.patterns p
                WHERE p.geometry IS NOT NULL
                AND ST_DWithin(
                    p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography,
                    :radius
                )
            ),
            routes_near_dest AS (
                -- Rutas que pasan cerca del destino
                SELECT DISTINCT p.id as pattern_id,
                       ST_Distance(
                           p.geometry::geography,
                           ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geography
                       ) as dist_from_dest
                FROM transporte.patterns p
                WHERE p.geometry IS NOT NULL
                AND ST_DWithin(
                    p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geography,
                    :radius
                )
            )
            SELECT 
                ro.pattern_id,
                l.nombre as nombre_linea,
                COALESCE(l.short_name, l.nombre) as short_name,
                COALESCE(l.long_name, l.nombre) as long_name,
                COALESCE(l.color, '0088FF') as color,
                COALESCE(l.text_color, 'FFFFFF') as text_color,
                ro.dist_from_origin,
                rd.dist_from_dest,
                (ro.dist_from_origin + rd.dist_from_dest) as total_dist
            FROM routes_near_origin ro
            JOIN routes_near_dest rd ON ro.pattern_id = rd.pattern_id
            JOIN transporte.patterns p ON ro.pattern_id = p.id
            JOIN transporte.lineas l ON p.id_linea = l.id_linea
            ORDER BY total_dist ASC
            LIMIT 30
        """)
        
        try:
            results = db.execute(query, {
                "from_lat": from_lat, "from_lon": from_lon,
                "to_lat": to_lat, "to_lon": to_lon,
                "radius": radius
            }).fetchall()
            print(f"[RoutePlanner] Routes by geometry found: {len(results)}")
            return results
        except Exception as e:
            print(f"[RoutePlanner] Error in _find_routes_by_geometry: {e}")
            return []


    def _find_direct_routes(self, db: Session, origin_stops, dest_stops):
        """Encuentra patrones que pasen por origen y destino (sin transbordo)"""
        origin_ids = [s.id_parada for s in origin_stops]
        dest_ids = [s.id_parada for s in dest_stops]
        
        if not origin_ids or not dest_ids:
            return []

        # Query simplificada sin DISTINCT para evitar problemas con ORDER BY
        query = text("""
            SELECT 
                p.id as pattern_id,
                l.nombre as nombre_linea,
                COALESCE(l.short_name, l.nombre) as short_name,
                COALESCE(l.long_name, l.nombre) as long_name,
                COALESCE(l.color, '0088FF') as color,
                COALESCE(l.text_color, 'FFFFFF') as text_color,
                ps1.id_parada as origin_stop_id,
                ps2.id_parada as dest_stop_id,
                ps1.sequence as seq_start,
                ps2.sequence as seq_end
            FROM transporte.patterns p
            JOIN transporte.lineas l ON p.id_linea = l.id_linea
            JOIN transporte.pattern_stops ps1 ON p.id = ps1.pattern_id
            JOIN transporte.pattern_stops ps2 ON p.id = ps2.pattern_id
            WHERE ps1.id_parada = ANY(:origin_ids)
            AND ps2.id_parada = ANY(:dest_ids)
            AND ps1.sequence < ps2.sequence
            ORDER BY (ps2.sequence - ps1.sequence) ASC
            LIMIT 20
        """)
        
        try:
            results = db.execute(query, {
                "origin_ids": origin_ids,
                "dest_ids": dest_ids
            }).fetchall()
            
            # Eliminar duplicados basados en pattern_id
            seen = set()
            unique_results = []
            for r in results:
                if r.pattern_id not in seen:
                    seen.add(r.pattern_id)
                    unique_results.append(r)
            
            return unique_results[:25]  # Aumentado para más opciones
        except Exception as e:
            print(f"[RoutePlanner] Error in _find_direct_routes: {e}")
            return []


    def _find_transfer_routes(self, db: Session, origin_stops, dest_stops):
        """
        Encuentra rutas con 1 transbordo.
        Busca: Origen -> Linea1 -> Parada de Transbordo -> Linea2 -> Destino
        """
        origin_ids = [s.id_parada for s in origin_stops]
        dest_ids = [s.id_parada for s in dest_stops]
        
        if not origin_ids or not dest_ids:
            return []

        # Buscar combinaciones de 2 líneas que conecten origen y destino
        query = text("""
            WITH origin_patterns AS (
                SELECT DISTINCT p.id as pattern_id, ps.id_parada, ps.sequence,
                       l.nombre as linea, l.short_name, l.long_name, l.color, l.text_color
                FROM transporte.patterns p
                JOIN transporte.lineas l ON p.id_linea = l.id_linea
                JOIN transporte.pattern_stops ps ON p.id = ps.pattern_id
                WHERE ps.id_parada = ANY(:origin_ids)
            ),
            dest_patterns AS (
                SELECT DISTINCT p.id as pattern_id, ps.id_parada, ps.sequence,
                       l.nombre as linea, l.short_name, l.long_name, l.color, l.text_color
                FROM transporte.patterns p
                JOIN transporte.lineas l ON p.id_linea = l.id_linea
                JOIN transporte.pattern_stops ps ON p.id = ps.pattern_id
                WHERE ps.id_parada = ANY(:dest_ids)
            ),
            transfer_points AS (
                -- Encontrar paradas donde ambas líneas pasan
                SELECT DISTINCT
                    op.pattern_id as pattern1_id,
                    op.linea as linea1,
                    op.short_name as short_name1,
                    op.long_name as long_name1,
                    op.color as color1,
                    op.text_color as text_color1,
                    op.id_parada as origin_stop,
                    op.sequence as origin_seq,
                    ps1.id_parada as transfer_stop,
                    ps1.sequence as transfer_seq1,
                    dp.pattern_id as pattern2_id,
                    dp.linea as linea2,
                    dp.short_name as short_name2,
                    dp.long_name as long_name2,
                    dp.color as color2,
                    dp.text_color as text_color2,
                    ps2.id_parada as transfer_stop2,
                    ps2.sequence as transfer_seq2,
                    dp.id_parada as dest_stop,
                    dp.sequence as dest_seq
                FROM origin_patterns op
                JOIN transporte.pattern_stops ps1 ON op.pattern_id = ps1.pattern_id
                JOIN transporte.pattern_stops ps2 ON ps1.id_parada = ps2.id_parada
                JOIN dest_patterns dp ON ps2.pattern_id = dp.pattern_id
                WHERE op.pattern_id != dp.pattern_id
                AND op.sequence < ps1.sequence
                AND ps2.sequence < dp.sequence
            )
            SELECT DISTINCT ON (pattern1_id, pattern2_id)
                tp.*,
                par.latitud as transfer_lat,
                par.longitud as transfer_lon,
                par.nombre_parada as transfer_name
            FROM transfer_points tp
            JOIN transporte.paradas par ON tp.transfer_stop = par.id_parada
            ORDER BY pattern1_id, pattern2_id, 
                     (transfer_seq1 - origin_seq) + (dest_seq - transfer_seq2)
            LIMIT 20
        """)
        
        try:
            return db.execute(query, {"origin_ids": origin_ids, "dest_ids": dest_ids}).fetchall()
        except Exception as e:
            print(f"[RoutePlanner] Error finding transfer routes: {e}")
            return []

    def _get_pattern_geometry(self, db: Session, pattern_id: str, from_seq: int = None, to_seq: int = None):
        """Obtiene los puntos de geometría REAL del patrón"""
        geom_query = text("""
            SELECT 
                ST_Y((dp).geom) as lat,
                ST_X((dp).geom) as lon
            FROM (
                SELECT ST_DumpPoints(geometry) as dp
                FROM transporte.patterns
                WHERE id = :pattern_id
            ) sub
            ORDER BY (dp).path[1]
        """)
        
        try:
            results = db.execute(geom_query, {"pattern_id": pattern_id}).fetchall()
            if results and len(results) > 2:
                coords = [(float(r.lat), float(r.lon)) for r in results]
                return coords
        except Exception as e:
            print(f"[RoutePlanner] Error getting geometry: {e}")
        
        return []

    def _get_stop_coords(self, db: Session, stop_id: int):
        """Obtiene coordenadas y nombre de una parada"""
        result = db.execute(
            text("SELECT latitud, longitud, nombre_parada FROM transporte.paradas WHERE id_parada = :id"),
            {"id": stop_id}
        ).fetchone()
        return result

    def _calculate_bus_time(self, distance_meters: float) -> int:
        """Calcula tiempo de viaje en bus en segundos"""
        return int((distance_meters / BUS_SPEED) * 60)

    def _calculate_walk_time(self, distance_meters: float) -> int:
        """Calcula tiempo caminando en segundos"""
        return int((distance_meters / WALK_SPEED) * 60)

    def _build_direct_itinerary(self, db: Session, route, from_lat, from_lon, to_lat, to_lon, start_time):
        """Construye itinerario para ruta directa (1 micro)"""
        origin_stop = self._get_stop_coords(db, route.origin_stop_id)
        dest_stop = self._get_stop_coords(db, route.dest_stop_id)
        
        if not origin_stop or not dest_stop:
            return None

        legs = []
        current_time = start_time
        total_walk_time = 0
        total_walk_dist = 0
        
        # Leg 1: Caminar a la parada
        walk_dist1 = haversine_distance(from_lat, from_lon, float(origin_stop.latitud), float(origin_stop.longitud))
        walk_time1 = self._calculate_walk_time(walk_dist1)
        
        walk_coords1 = [(from_lat, from_lon), (float(origin_stop.latitud), float(origin_stop.longitud))]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time1 * 1000),
            duration=float(walk_time1),
            distance=walk_dist1,
            from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
            to=PlaceSchema(lat=float(origin_stop.latitud), lon=float(origin_stop.longitud), name=origin_stop.nombre_parada),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords1), length=len(walk_coords1))
        ))
        current_time += walk_time1 * 1000
        total_walk_time += walk_time1
        total_walk_dist += walk_dist1
        
        # Tiempo de espera
        wait_time = WAIT_TIME_MINUTES * 60
        current_time += wait_time * 1000
        
        # Leg 2: Viaje en bus
        bus_coords = self._get_pattern_geometry(db, route.pattern_id, route.seq_start, route.seq_end)
        if not bus_coords:
            bus_coords = [
                (float(origin_stop.latitud), float(origin_stop.longitud)),
                (float(dest_stop.latitud), float(dest_stop.longitud))
            ]
        
        bus_dist = haversine_distance(
            float(origin_stop.latitud), float(origin_stop.longitud),
            float(dest_stop.latitud), float(dest_stop.longitud)
        )
        bus_time = self._calculate_bus_time(bus_dist)
        
        legs.append(LegSchema(
            mode="BUS",
            startTime=current_time,
            endTime=current_time + (bus_time * 1000),
            duration=float(bus_time),
            distance=bus_dist,
            from_=PlaceSchema(lat=float(origin_stop.latitud), lon=float(origin_stop.longitud), name=origin_stop.nombre_parada),
            to=PlaceSchema(lat=float(dest_stop.latitud), lon=float(dest_stop.longitud), name=dest_stop.nombre_parada),
            route=route.nombre_linea,
            routeId=route.pattern_id,
            routeShortName=route.short_name or route.nombre_linea,
            routeLongName=route.long_name or f"Línea {route.nombre_linea}",
            routeColor=route.color or "0088FF",
            routeTextColor=route.text_color or "FFFFFF",
            legGeometry=LegGeometry(points=encode_polyline(bus_coords), length=len(bus_coords)),
            transitLeg=True
        ))
        current_time += bus_time * 1000
        
        # Leg 3: Caminar al destino
        walk_dist2 = haversine_distance(float(dest_stop.latitud), float(dest_stop.longitud), to_lat, to_lon)
        walk_time2 = self._calculate_walk_time(walk_dist2)
        
        walk_coords2 = [(float(dest_stop.latitud), float(dest_stop.longitud)), (to_lat, to_lon)]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time2 * 1000),
            duration=float(walk_time2),
            distance=walk_dist2,
            from_=PlaceSchema(lat=float(dest_stop.latitud), lon=float(dest_stop.longitud), name=dest_stop.nombre_parada),
            to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination"),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords2), length=len(walk_coords2))
        ))
        current_time += walk_time2 * 1000
        total_walk_time += walk_time2
        total_walk_dist += walk_dist2
        
        total_duration = (current_time - start_time) // 1000
        transit_time = bus_time
        
        return ItinerarySchema(
            legs=legs,
            startTime=start_time,
            endTime=current_time,
            duration=total_duration,
            walkTime=total_walk_time,
            walkDistance=total_walk_dist,
            transfers=0,
            transitTime=transit_time,
            waitingTime=wait_time
        )

    def _build_geometry_itinerary(self, db: Session, route, from_lat, from_lon, to_lat, to_lon, start_time):
        """
        Construye itinerario basado en geometría del trazado.
        El usuario puede subir/bajar en cualquier punto de la ruta.
        """
        legs = []
        current_time = start_time
        total_walk_time = 0
        total_walk_dist = 0
        
        # Obtener el trazado completo de la ruta
        bus_coords = self._get_route_geometry(db, route.pattern_id)
        if not bus_coords or len(bus_coords) < 2:
            return None
        
        # Encontrar el punto más cercano al origen y destino en el trazado
        origin_point, origin_idx = self._find_closest_point_on_line(bus_coords, from_lat, from_lon)
        dest_point, dest_idx = self._find_closest_point_on_line(bus_coords, to_lat, to_lon)
        
        # Verificar que el origen viene antes del destino en la ruta
        if origin_idx >= dest_idx:
            return None
        
        # Leg 1: Caminar al punto de subida (cualquier punto de la ruta)
        walk_dist1 = haversine_distance(from_lat, from_lon, origin_point[0], origin_point[1])
        walk_time1 = self._calculate_walk_time(walk_dist1)
        
        walk_coords1 = [(from_lat, from_lon), origin_point]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time1 * 1000),
            duration=float(walk_time1),
            distance=walk_dist1,
            from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
            to=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding point"),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords1), length=len(walk_coords1))
        ))
        current_time += walk_time1 * 1000
        total_walk_time += walk_time1
        total_walk_dist += walk_dist1
        
        # Tiempo de espera del micro
        wait_time = WAIT_TIME_MINUTES * 60
        current_time += wait_time * 1000
        
        # Leg 2: Viaje en micro (siguiendo el trazado real)
        # Extraer solo la porción del trazado entre origen y destino
        route_segment = bus_coords[origin_idx:dest_idx+1]
        bus_distance = 0
        for i in range(len(route_segment) - 1):
            bus_distance += haversine_distance(
                route_segment[i][0], route_segment[i][1],
                route_segment[i+1][0], route_segment[i+1][1]
            )
        bus_time = self._calculate_bus_time(bus_distance)
        
        legs.append(LegSchema(
            mode="BUS",
            startTime=current_time,
            endTime=current_time + (bus_time * 1000),
            duration=float(bus_time),
            distance=bus_distance,
            from_=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding"),
            to=PlaceSchema(lat=dest_point[0], lon=dest_point[1], name="Bus alighting"),
            route=route.nombre_linea,
            routeId=route.pattern_id,
            routeShortName=route.short_name or route.nombre_linea,
            routeLongName=route.long_name or f"Línea {route.nombre_linea}",
            routeColor=route.color or "0088FF",
            routeTextColor=route.text_color or "FFFFFF",
            legGeometry=LegGeometry(points=encode_polyline(route_segment), length=len(route_segment)),
            transitLeg=True
        ))
        current_time += bus_time * 1000
        
        # Leg 3: Caminar al destino final
        walk_dist2 = haversine_distance(dest_point[0], dest_point[1], to_lat, to_lon)
        walk_time2 = self._calculate_walk_time(walk_dist2)
        
        walk_coords2 = [dest_point, (to_lat, to_lon)]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time2 * 1000),
            duration=float(walk_time2),
            distance=walk_dist2,
            from_=PlaceSchema(lat=dest_point[0], lon=dest_point[1], name="Bus alighting"),
            to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination"),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords2), length=len(walk_coords2))
        ))
        current_time += walk_time2 * 1000
        total_walk_time += walk_time2
        total_walk_dist += walk_dist2
        
        total_duration = (current_time - start_time) // 1000
        
        return ItinerarySchema(
            legs=legs,
            startTime=start_time,
            endTime=current_time,
            duration=total_duration,
            walkTime=total_walk_time,
            walkDistance=total_walk_dist,
            transfers=0,
            transitTime=bus_time,
            waitingTime=wait_time
        )

    def _find_closest_point_on_line(self, coords, lat, lon):
        """Encuentra el punto más cercano en una línea de coordenadas"""
        min_dist = float('inf')
        closest_point = coords[0]
        closest_idx = 0
        
        for i, point in enumerate(coords):
            dist = haversine_distance(lat, lon, point[0], point[1])
            if dist < min_dist:
                min_dist = dist
                closest_point = point
                closest_idx = i
        
        return closest_point, closest_idx

    def _build_transfer_itinerary(self, db: Session, route, from_lat, from_lon, to_lat, to_lon, start_time):
        """Construye itinerario con 1 transbordo (2 micros)"""
        origin_stop = self._get_stop_coords(db, route.origin_stop)
        transfer_stop = self._get_stop_coords(db, route.transfer_stop)
        dest_stop = self._get_stop_coords(db, route.dest_stop)
        
        if not origin_stop or not transfer_stop or not dest_stop:
            return None

        legs = []
        current_time = start_time
        total_walk_time = 0
        total_walk_dist = 0
        total_transit_time = 0
        total_wait_time = 0
        
        # Leg 1: Caminar a la primera parada
        walk_dist1 = haversine_distance(from_lat, from_lon, float(origin_stop.latitud), float(origin_stop.longitud))
        walk_time1 = self._calculate_walk_time(walk_dist1)
        
        walk_coords1 = [(from_lat, from_lon), (float(origin_stop.latitud), float(origin_stop.longitud))]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time1 * 1000),
            duration=float(walk_time1),
            distance=walk_dist1,
            from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
            to=PlaceSchema(lat=float(origin_stop.latitud), lon=float(origin_stop.longitud), name=origin_stop.nombre_parada),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords1), length=len(walk_coords1))
        ))
        current_time += walk_time1 * 1000
        total_walk_time += walk_time1
        total_walk_dist += walk_dist1
        
        # Espera para bus 1
        wait_time1 = WAIT_TIME_MINUTES * 60
        current_time += wait_time1 * 1000
        total_wait_time += wait_time1
        
        # Leg 2: Primer bus (hasta transbordo)
        bus1_coords = self._get_pattern_geometry(db, route.pattern1_id)
        if not bus1_coords:
            bus1_coords = [
                (float(origin_stop.latitud), float(origin_stop.longitud)),
                (float(transfer_stop.latitud), float(transfer_stop.longitud))
            ]
        
        bus1_dist = haversine_distance(
            float(origin_stop.latitud), float(origin_stop.longitud),
            float(transfer_stop.latitud), float(transfer_stop.longitud)
        )
        bus1_time = self._calculate_bus_time(bus1_dist)
        
        legs.append(LegSchema(
            mode="BUS",
            startTime=current_time,
            endTime=current_time + (bus1_time * 1000),
            duration=float(bus1_time),
            distance=bus1_dist,
            from_=PlaceSchema(lat=float(origin_stop.latitud), lon=float(origin_stop.longitud), name=origin_stop.nombre_parada),
            to=PlaceSchema(lat=float(transfer_stop.latitud), lon=float(transfer_stop.longitud), name=route.transfer_name),
            route=route.linea1,
            routeId=route.pattern1_id,
            routeShortName=route.short_name1 or route.linea1,
            routeLongName=route.long_name1 or f"Línea {route.linea1}",
            routeColor=route.color1 or "0088FF",
            routeTextColor=route.text_color1 or "FFFFFF",
            legGeometry=LegGeometry(points=encode_polyline(bus1_coords), length=len(bus1_coords)),
            transitLeg=True
        ))
        current_time += bus1_time * 1000
        total_transit_time += bus1_time
        
        # Tiempo de transbordo (caminar + esperar)
        transfer_wait = TRANSFER_TIME_MINUTES * 60
        current_time += transfer_wait * 1000
        total_wait_time += transfer_wait
        
        # Espera para bus 2
        wait_time2 = WAIT_TIME_MINUTES * 60
        current_time += wait_time2 * 1000
        total_wait_time += wait_time2
        
        # Leg 3: Segundo bus
        bus2_coords = self._get_pattern_geometry(db, route.pattern2_id)
        if not bus2_coords:
            bus2_coords = [
                (float(transfer_stop.latitud), float(transfer_stop.longitud)),
                (float(dest_stop.latitud), float(dest_stop.longitud))
            ]
        
        bus2_dist = haversine_distance(
            float(transfer_stop.latitud), float(transfer_stop.longitud),
            float(dest_stop.latitud), float(dest_stop.longitud)
        )
        bus2_time = self._calculate_bus_time(bus2_dist)
        
        legs.append(LegSchema(
            mode="BUS",
            startTime=current_time,
            endTime=current_time + (bus2_time * 1000),
            duration=float(bus2_time),
            distance=bus2_dist,
            from_=PlaceSchema(lat=float(transfer_stop.latitud), lon=float(transfer_stop.longitud), name=route.transfer_name),
            to=PlaceSchema(lat=float(dest_stop.latitud), lon=float(dest_stop.longitud), name=dest_stop.nombre_parada),
            route=route.linea2,
            routeId=route.pattern2_id,
            routeShortName=route.short_name2 or route.linea2,
            routeLongName=route.long_name2 or f"Línea {route.linea2}",
            routeColor=route.color2 or "FF5722",  # Color diferente para segundo bus
            routeTextColor=route.text_color2 or "FFFFFF",
            legGeometry=LegGeometry(points=encode_polyline(bus2_coords), length=len(bus2_coords)),
            transitLeg=True
        ))
        current_time += bus2_time * 1000
        total_transit_time += bus2_time
        
        # Leg 4: Caminar al destino
        walk_dist2 = haversine_distance(float(dest_stop.latitud), float(dest_stop.longitud), to_lat, to_lon)
        walk_time2 = self._calculate_walk_time(walk_dist2)
        
        walk_coords2 = [(float(dest_stop.latitud), float(dest_stop.longitud)), (to_lat, to_lon)]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time2 * 1000),
            duration=float(walk_time2),
            distance=walk_dist2,
            from_=PlaceSchema(lat=float(dest_stop.latitud), lon=float(dest_stop.longitud), name=dest_stop.nombre_parada),
            to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination"),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords2), length=len(walk_coords2))
        ))
        current_time += walk_time2 * 1000
        total_walk_time += walk_time2
        total_walk_dist += walk_dist2
        
        total_duration = (current_time - start_time) // 1000
        
        return ItinerarySchema(
            legs=legs,
            startTime=start_time,
            endTime=current_time,
            duration=total_duration,
            walkTime=total_walk_time,
            walkDistance=total_walk_dist,
            transfers=1,  # 1 transbordo
            transitTime=total_transit_time,
            waitingTime=total_wait_time
        )

    def _build_walk_only_itinerary(self, from_lat, from_lon, to_lat, to_lon, start_time):
        """Construye itinerario solo a pie (fallback)"""
        distance = haversine_distance(from_lat, from_lon, to_lat, to_lon)
        walk_time = self._calculate_walk_time(distance)
        
        walk_coords = [(from_lat, from_lon), (to_lat, to_lon)]
        
        legs = [LegSchema(
            mode="WALK",
            startTime=start_time,
            endTime=start_time + (walk_time * 1000),
            duration=float(walk_time),
            distance=distance,
            from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
            to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination"),
            route="",
            legGeometry=LegGeometry(points=encode_polyline(walk_coords), length=len(walk_coords))
        )]
        
        return ItinerarySchema(
            legs=legs,
            startTime=start_time,
            endTime=start_time + (walk_time * 1000),
            duration=walk_time,
            walkTime=walk_time,
            walkDistance=distance,
            transfers=0,
            transitTime=0,
            waitingTime=0
        )


# Singleton para usar en la aplicación
route_planner = RoutePlanner()
