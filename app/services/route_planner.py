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
WALK_SPEED = 70  # ~4.2 km/h (ligeramente más lento para penalizar caminatas largas)
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
    """Calcula distancia en línea recta (como el vuelo de un pájaro)"""
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def walking_distance_realistic(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distancia REALISTA caminando siguiendo calles.
    
    En lugar de línea recta (que atraviesa casas), aproxima que el usuario
    sigue la red vial de Santa Cruz (calles en cuadrícula).
    
    Factor de corrección según distancia:
    - <200m: factor 1.3 (solo esquinas, casi directo)
    - 200-500m: factor 1.5 (algunas cuadras)
    - 500-1000m: factor 1.7 (varias cuadras)
    - >1000m: factor 2.0 (muchas cuadras, más desviaciones)
    
    NOTA: Para cálculo exacto necesitarías:
    - Red vial completa en PostGIS con pgrouting
    - O servicio de routing (OSRM, GraphHopper)
    """
    straight_distance = haversine_distance(lat1, lon1, lat2, lon2)
    
    # Factor de corrección según distancia (calles en cuadrícula)
    if straight_distance < 200:
        factor = 1.3  # Casi directo, solo esquinas
    elif straight_distance < 500:
        factor = 1.5  # Algunas cuadras
    elif straight_distance < 1000:
        factor = 1.7  # Varias cuadras
    else:
        factor = 2.0  # Muchas cuadras, más desviaciones
    
    # Aplicar factor para simular seguir calles
    realistic_distance = straight_distance * factor
    
    return realistic_distance


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
        num_itineraries: int = 10,
        max_transfers: int = 3  # NUEVO: Permitir hasta 3 transbordos (4 micros)
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
        
        # Radio de búsqueda adaptativo para Santa Cruz
        # En SCZ los micros paran en cualquier cuadra, optimizamos por geometría
        if direct_distance < 2000:
            geometry_radius = 800
            stop_radius = 1200
        elif direct_distance < 5000:
            geometry_radius = 1500
            stop_radius = 2000
        else:
            geometry_radius = 2500
            stop_radius = 3000
        
        # ===== MÉTODO 1: Buscar rutas por GEOMETRÍA (PRIORITARIO) =====
        # En Santa Cruz los micros paran en cualquier cuadra
        print(f"[RoutePlanner] 🔍 Modo Santa Cruz: búsqueda por geometría (radius={geometry_radius}m)")
        geometry_routes = self._find_routes_by_geometry(
            db, from_lat, from_lon, to_lat, to_lon, radius=geometry_radius
        )
        
        # Procesar TODAS las rutas por geometría encontradas
        geometry_success = 0
        geometry_failed = 0
        for route in geometry_routes[:100]:
            try:
                itinerary = self._build_geometry_itinerary(
                    db, route, from_lat, from_lon, to_lat, to_lon, current_time
                )
                if itinerary:
                    itineraries.append(itinerary)
                    geometry_success += 1
                else:
                    geometry_failed += 1
            except Exception as e:
                geometry_failed += 1
                print(f"[RoutePlanner] Error en geometría de línea {route.short_name}: {e}")
        
        print(f"[RoutePlanner] ✅ Rutas por geometría: {geometry_success} exitosas, {geometry_failed} fallidas")
        
        # ===== MÉTODO 2: Buscar por paradas (secundario) =====
        if len(itineraries) < num_itineraries:
            origin_stops = self._find_nearby_stops(db, from_lat, from_lon, radius=stop_radius, limit=50)
            dest_stops = self._find_nearby_stops(db, to_lat, to_lon, radius=stop_radius, limit=50)
            
            print(f"[RoutePlanner] Origin stops: {len(origin_stops)}, Dest stops: {len(dest_stops)}")
            
            direct_routes = self._find_direct_routes(db, origin_stops, dest_stops)
            print(f"[RoutePlanner] Direct routes found: {len(direct_routes)}")
            
            # Procesar más rutas directas (aumentado de 10 a 25)
            for route in direct_routes[:25]:
                itinerary = self._build_direct_itinerary(
                    db, route, from_lat, from_lon, to_lat, to_lon, current_time
                )
                if itinerary:
                    itineraries.append(itinerary)
        
        # ===== MÉTODO 3: Rutas con 1 transbordo (2 micros) =====
        print("[RoutePlanner] 🔄 Buscando transbordos (2 micros)...")
        transfer_routes_geom = self._find_transfer_routes_by_geometry(
            db, from_lat, from_lon, to_lat, to_lon, radius=geometry_radius
        )
        print(f"[RoutePlanner] 🔄 Transbordos por geometría: {len(transfer_routes_geom)}")
        
        for route in transfer_routes_geom[:50]:
            itinerary = self._build_transfer_itinerary_by_geometry(
                db, route, from_lat, from_lon, to_lat, to_lon, current_time
            )
            if itinerary and itinerary.walkDistance < 1000:
                itineraries.append(itinerary)
        
        # ===== MÉTODO 4: Rutas con 2 transbordos (3 micros) =====
        if max_transfers >= 2 and len(itineraries) < num_itineraries:
            print("[RoutePlanner] 🔄🔄 Buscando rutas con 2 transbordos (3 micros)...")
            triple_routes = self._find_triple_transfer_routes(
                db, from_lat, from_lon, to_lat, to_lon, radius=geometry_radius
            )
            print(f"[RoutePlanner] 🔄🔄 Rutas con 2 transbordos: {len(triple_routes)}")
            
            for route in triple_routes[:30]:
                itinerary = self._build_triple_transfer_itinerary(
                    db, route, from_lat, from_lon, to_lat, to_lon, current_time
                )
                if itinerary and itinerary.walkDistance < 800:  # Más estricto para 3 micros
                    itineraries.append(itinerary)
        
        # ===== MÉTODO 5: Rutas con 3 transbordos (4 micros) =====
        if max_transfers >= 3 and len(itineraries) < num_itineraries:
            print("[RoutePlanner] 🔄🔄🔄 Buscando rutas con 3 transbordos (4 micros)...")
            quadruple_routes = self._find_quadruple_transfer_routes(
                db, from_lat, from_lon, to_lat, to_lon, radius=geometry_radius
            )
            print(f"[RoutePlanner] 🔄🔄🔄 Rutas con 3 transbordos: {len(quadruple_routes)}")
            
            for route in quadruple_routes[:20]:
                itinerary = self._build_quadruple_transfer_itinerary(
                    db, route, from_lat, from_lon, to_lat, to_lon, current_time
                )
                if itinerary and itinerary.walkDistance < 600:  # Muy estricto para 4 micros
                    itineraries.append(itinerary)
        
        # 3. Ordenar por "Costo Generalizado" - PRIORIDAD: MINIMIZAR CAMINATA
        def calculate_generalized_cost(itinerary):
            # CAMBIO CRÍTICO: Penalizar MUCHO MÁS la caminata
            walk_penalty = 5.0  # Aumentado de 2.5 a 5.0
            wait_penalty = 1.0
            transfer_penalty = 240  # Reducido de 420 a 240 (4 min) - MEJOR hacer transbordo que caminar
            transit_weight = 1.0
            
            # Penalización AGRESIVA por caminata excesiva
            excess_walk_penalty = 0
            if itinerary.walkDistance > 300:  # Más estricto: desde 300m
                excess_walk_penalty = (itinerary.walkDistance - 300) * 2.0
            if itinerary.walkDistance > 800:  # Desde 800m penalizar MÁS
                excess_walk_penalty += (itinerary.walkDistance - 800) * 4.0
            if itinerary.walkDistance > 1500:  # Más de 1.5km es INACEPTABLE
                excess_walk_penalty += (itinerary.walkDistance - 1500) * 10.0
            
            # Bonificación para rutas directas SOLO si la caminata es razonable
            direct_bonus = 0
            if itinerary.transfers == 0 and itinerary.walkDistance < 500:
                direct_bonus = -200  # Solo bonificar si camina poco
            
            # Penalizar rutas que dan muchas vueltas
            total_distance = sum(leg.distance for leg in itinerary.legs if leg.mode == "BUS")
            route_efficiency = 1.5 if total_distance > direct_distance * 2.0 else 1.0

            cost = (itinerary.transitTime * transit_weight * route_efficiency) + \
                   (itinerary.walkTime * walk_penalty) + \
                   (itinerary.waitingTime * wait_penalty) + \
                   (itinerary.transfers * transfer_penalty) + \
                   excess_walk_penalty + direct_bonus
                   
            return cost

        itineraries.sort(key=calculate_generalized_cost)
        
        # Mostrar info de las mejores rutas para debugging
        print(f"[RoutePlanner] 📊 Top 3 rutas antes de filtrar:")
        for i, it in enumerate(itineraries[:3], 1):
            transfers_text = f"{it.transfers} transbordo(s)" if it.transfers > 0 else "directo"
            print(f"   {i}. Caminata: {it.walkDistance:.0f}m, Tiempo: {it.duration//60}min, {transfers_text}")
        
        # Filtrar solo rutas absurdamente malas (>2km caminata) si hay mejores opciones
        if len(itineraries) > 3:
            best_walk = min(it.walkDistance for it in itineraries[:5])
            if best_walk < 1000:
                itineraries = [it for it in itineraries if it.walkDistance < 2000 or itineraries.index(it) < 3]

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
            AND activa = true
            ORDER BY distance ASC
            LIMIT :limit
        """)
        result = db.execute(query, {"lat": lat, "lon": lon, "radius": radius, "limit": limit}).fetchall()
        print(f"[RoutePlanner] Paradas encontradas a {radius}m: {len(result)}")
        if result:
            print(f"   Más cercana: {result[0].nombre_parada} a {result[0].distance:.0f}m")
        return result

    def _find_routes_by_geometry(self, db: Session, from_lat: float, from_lon: float, 
                                  to_lat: float, to_lon: float, radius: int = 300):
        """
        Encuentra rutas cuya GEOMETRÍA pase cerca del origen y destino.
        En Santa Cruz, los micros paran en cualquier esquina.
        """
        query = text("""
            WITH routes_near_origin AS (
                SELECT DISTINCT p.id as pattern_id, 
                       p.id_linea,
                       p.sentido,
                       ST_Distance(
                           p.geometry::geography,
                           ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography
                       ) as dist_from_origin,
                       ST_Length(p.geometry::geography) as route_length
                FROM transporte.patterns p
                WHERE p.geometry IS NOT NULL
                AND ST_DWithin(
                    p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography,
                    :radius
                )
            ),
            routes_near_dest AS (
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
                ro.route_length,
                ro.sentido,
                (ro.dist_from_origin + rd.dist_from_dest) as total_walk_dist
            FROM routes_near_origin ro
            JOIN routes_near_dest rd ON ro.pattern_id = rd.pattern_id
            JOIN transporte.patterns p ON ro.pattern_id = p.id
            JOIN transporte.lineas l ON p.id_linea = l.id_linea
            WHERE l.activa = true
            ORDER BY total_walk_dist ASC, ro.route_length ASC
            LIMIT 200
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
            LIMIT 50
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

    def _find_transfer_routes_by_geometry(self, db: Session, from_lat: float, from_lon: float,
                                          to_lat: float, to_lon: float, radius: int = 1500):
        """
        SOLUCIÓN DEFINITIVA: Busca transbordos usando GEOMETRÍA de rutas.
        Encuentra líneas que pasen cerca del origen Y líneas que pasen cerca del destino,
        luego busca puntos de intersección cercanos entre ambas geometrías.
        """
        query = text("""
            WITH routes_near_origin AS (
                SELECT DISTINCT 
                    p.id as pattern1_id,
                    p.id_linea as linea1_id,
                    l1.nombre as linea1,
                    l1.short_name as short_name1,
                    l1.long_name as long_name1,
                    l1.color as color1,
                    l1.text_color as text_color1,
                    ST_Distance(
                        p.geometry::geography,
                        ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography
                    ) as dist_from_origin
                FROM transporte.patterns p
                JOIN transporte.lineas l1 ON p.id_linea = l1.id_linea
                WHERE p.geometry IS NOT NULL
                AND l1.activa = true
                AND ST_DWithin(
                    p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography,
                    :radius
                )
            ),
            routes_near_dest AS (
                SELECT DISTINCT 
                    p.id as pattern2_id,
                    p.id_linea as linea2_id,
                    l2.nombre as linea2,
                    l2.short_name as short_name2,
                    l2.long_name as long_name2,
                    l2.color as color2,
                    l2.text_color as text_color2,
                    ST_Distance(
                        p.geometry::geography,
                        ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geography
                    ) as dist_from_dest
                FROM transporte.patterns p
                JOIN transporte.lineas l2 ON p.id_linea = l2.id_linea
                WHERE p.geometry IS NOT NULL
                AND l2.activa = true
                AND ST_DWithin(
                    p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geography,
                    :radius
                )
            ),
            intersecting_routes AS (
                -- Encontrar rutas que se cruzan (puntos cercanos entre geometrías)
                SELECT DISTINCT
                    ro.pattern1_id,
                    ro.linea1,
                    ro.short_name1,
                    ro.long_name1,
                    ro.color1,
                    ro.text_color1,
                    ro.dist_from_origin,
                    rd.pattern2_id,
                    rd.linea2,
                    rd.short_name2,
                    rd.long_name2,
                    rd.color2,
                    rd.text_color2,
                    rd.dist_from_dest,
                    ST_Distance(
                        p1.geometry::geography,
                        p2.geometry::geography
                    ) as routes_distance,
                    ST_ClosestPoint(p1.geometry, p2.geometry) as transfer_point
                FROM routes_near_origin ro
                JOIN routes_near_dest rd ON ro.linea1_id != rd.linea2_id
                JOIN transporte.patterns p1 ON ro.pattern1_id = p1.id
                JOIN transporte.patterns p2 ON rd.pattern2_id = p2.id
                WHERE ST_DWithin(
                    p1.geometry::geography,
                    p2.geometry::geography,
                    500  -- Rutas deben estar a menos de 500m entre sí
                )
            )
            SELECT 
                ir.*,
                ST_Y(ir.transfer_point) as transfer_lat,
                ST_X(ir.transfer_point) as transfer_lon,
                (ir.dist_from_origin + ir.dist_from_dest + ir.routes_distance) as total_walk_estimate
            FROM intersecting_routes ir
            ORDER BY total_walk_estimate ASC
            LIMIT 100
        """)
        
        try:
            results = db.execute(query, {
                "from_lat": from_lat, "from_lon": from_lon,
                "to_lat": to_lat, "to_lon": to_lon,
                "radius": radius
            }).fetchall()
            return results
        except Exception as e:
            print(f"[RoutePlanner] Error en _find_transfer_routes_by_geometry: {e}")
            return []

    def _build_transfer_itinerary_by_geometry(self, db: Session, route, from_lat, from_lon, to_lat, to_lon, start_time):
        """
        Construye itinerario con transbordo usando GEOMETRÍA (punto de intersección).
        SOLUCIÓN DEFINITIVA: No depende de paradas oficiales.
        """
        try:
            transfer_lat = float(route.transfer_lat)
            transfer_lon = float(route.transfer_lon)
            
            # Obtener geometrías de ambas líneas
            bus1_coords = self._get_pattern_geometry(db, route.pattern1_id)
            bus2_coords = self._get_pattern_geometry(db, route.pattern2_id)
            
            if not bus1_coords or not bus2_coords or len(bus1_coords) < 2 or len(bus2_coords) < 2:
                return None
            
            # Encontrar puntos más cercanos en cada línea
            origin_point, origin_idx = self._find_closest_point_on_line(bus1_coords, from_lat, from_lon)
            transfer_point1, transfer_idx1 = self._find_closest_point_on_line(bus1_coords, transfer_lat, transfer_lon)
            transfer_point2, transfer_idx2 = self._find_closest_point_on_line(bus2_coords, transfer_lat, transfer_lon)
            dest_point, dest_idx = self._find_closest_point_on_line(bus2_coords, to_lat, to_lon)
            
            # Validar que el orden es correcto
            if origin_idx >= transfer_idx1 or transfer_idx2 >= dest_idx:
                return None
            
            # Validar caminata total (siguiendo calles)
            walk_to_first = walking_distance_realistic(from_lat, from_lon, origin_point[0], origin_point[1])
            walk_transfer = walking_distance_realistic(transfer_point1[0], transfer_point1[1], transfer_point2[0], transfer_point2[1])
            walk_from_last = walking_distance_realistic(dest_point[0], dest_point[1], to_lat, to_lon)
            total_walk = walk_to_first + walk_transfer + walk_from_last
            
            if total_walk > 1000:  # Máximo 1km caminata total
                return None
            
            legs = []
            current_time = start_time
            total_walk_time = 0
            total_walk_dist = 0
            total_transit_time = 0
            total_wait_time = 0
            
            # Leg 1: Caminar a primera línea
            walk_time1 = self._calculate_walk_time(walk_to_first)
            legs.append(LegSchema(
                mode="WALK",
                startTime=current_time,
                endTime=current_time + (walk_time1 * 1000),
                duration=float(walk_time1),
                distance=walk_to_first,
                from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
                to=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding"),
                legGeometry=LegGeometry(points=encode_polyline([(from_lat, from_lon), origin_point]), length=2)
            ))
            current_time += walk_time1 * 1000
            total_walk_time += walk_time1
            total_walk_dist += walk_to_first
            
            # Espera bus 1
            wait_time1 = WAIT_TIME_MINUTES * 60
            current_time += wait_time1 * 1000
            total_wait_time += wait_time1
            
            # Leg 2: Primer bus hasta transbordo
            route_segment1 = bus1_coords[origin_idx:transfer_idx1+1]
            bus1_dist = sum(haversine_distance(route_segment1[i][0], route_segment1[i][1],
                                               route_segment1[i+1][0], route_segment1[i+1][1])
                           for i in range(len(route_segment1)-1))
            bus1_time = self._calculate_bus_time(bus1_dist)
            
            legs.append(LegSchema(
                mode="BUS",
                startTime=current_time,
                endTime=current_time + (bus1_time * 1000),
                duration=float(bus1_time),
                distance=bus1_dist,
                from_=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding"),
                to=PlaceSchema(lat=transfer_point1[0], lon=transfer_point1[1], name="Transfer point"),
                route=route.linea1,
                routeId=route.pattern1_id,
                routeShortName=route.short_name1 or route.linea1,
                routeLongName=route.long_name1 or f"Línea {route.linea1}",
                routeColor=route.color1 or "0088FF",
                routeTextColor=route.text_color1 or "FFFFFF",
                legGeometry=LegGeometry(points=encode_polyline(route_segment1), length=len(route_segment1)),
                transitLeg=True
            ))
            current_time += bus1_time * 1000
            total_transit_time += bus1_time
            
            # Leg 3: Caminar entre transbordos
            walk_time_transfer = self._calculate_walk_time(walk_transfer)
            legs.append(LegSchema(
                mode="WALK",
                startTime=current_time,
                endTime=current_time + (walk_time_transfer * 1000),
                duration=float(walk_time_transfer),
                distance=walk_transfer,
                from_=PlaceSchema(lat=transfer_point1[0], lon=transfer_point1[1], name="Transfer point"),
                to=PlaceSchema(lat=transfer_point2[0], lon=transfer_point2[1], name="Transfer point"),
                legGeometry=LegGeometry(points=encode_polyline([transfer_point1, transfer_point2]), length=2)
            ))
            current_time += walk_time_transfer * 1000
            total_walk_time += walk_time_transfer
            total_walk_dist += walk_transfer
            
            # Espera bus 2
            wait_time2 = WAIT_TIME_MINUTES * 60
            current_time += wait_time2 * 1000
            total_wait_time += wait_time2
            
            # Leg 4: Segundo bus hasta destino
            route_segment2 = bus2_coords[transfer_idx2:dest_idx+1]
            bus2_dist = sum(haversine_distance(route_segment2[i][0], route_segment2[i][1],
                                               route_segment2[i+1][0], route_segment2[i+1][1])
                           for i in range(len(route_segment2)-1))
            bus2_time = self._calculate_bus_time(bus2_dist)
            
            legs.append(LegSchema(
                mode="BUS",
                startTime=current_time,
                endTime=current_time + (bus2_time * 1000),
                duration=float(bus2_time),
                distance=bus2_dist,
                from_=PlaceSchema(lat=transfer_point2[0], lon=transfer_point2[1], name="Transfer point"),
                to=PlaceSchema(lat=dest_point[0], lon=dest_point[1], name="Bus alighting"),
                route=route.linea2,
                routeId=route.pattern2_id,
                routeShortName=route.short_name2 or route.linea2,
                routeLongName=route.long_name2 or f"Línea {route.linea2}",
                routeColor=route.color2 or "FF5722",
                routeTextColor=route.text_color2 or "FFFFFF",
                legGeometry=LegGeometry(points=encode_polyline(route_segment2), length=len(route_segment2)),
                transitLeg=True
            ))
            current_time += bus2_time * 1000
            total_transit_time += bus2_time
            
            # Leg 5: Caminar al destino final
            walk_time2 = self._calculate_walk_time(walk_from_last)
            legs.append(LegSchema(
                mode="WALK",
                startTime=current_time,
                endTime=current_time + (walk_time2 * 1000),
                duration=float(walk_time2),
                distance=walk_from_last,
                from_=PlaceSchema(lat=dest_point[0], lon=dest_point[1], name="Bus alighting"),
                to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination"),
                legGeometry=LegGeometry(points=encode_polyline([dest_point, (to_lat, to_lon)]), length=2)
            ))
            current_time += walk_time2 * 1000
            total_walk_time += walk_time2
            total_walk_dist += walk_from_last
            
            total_duration = (current_time - start_time) // 1000
            
            return ItinerarySchema(
                legs=legs,
                startTime=start_time,
                endTime=current_time,
                duration=total_duration,
                walkTime=total_walk_time,
                walkDistance=total_walk_dist,
                transfers=1,
                transitTime=total_transit_time,
                waitingTime=total_wait_time
            )
        except Exception as e:
            print(f"[RoutePlanner] Error en _build_transfer_itinerary_by_geometry: {e}")
            return None

    def _find_triple_transfer_routes(self, db: Session, from_lat: float, from_lon: float,
                                    to_lat: float, to_lon: float, radius: int = 1500):
        """
        Encuentra rutas con 2 transbordos (3 micros).
        Busca: Origen -> Línea1 -> Transbordo1 -> Línea2 -> Transbordo2 -> Línea3 -> Destino
        """
        query = text("""
            WITH routes_near_origin AS (
                SELECT DISTINCT p.id as pattern1_id, p.id_linea as linea1_id,
                       l1.short_name as short_name1, l1.nombre as linea1,
                       l1.color as color1, l1.text_color as text_color1
                FROM transporte.patterns p
                JOIN transporte.lineas l1 ON p.id_linea = l1.id_linea
                WHERE p.geometry IS NOT NULL AND l1.activa = true
                AND ST_DWithin(p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:from_lon, :from_lat), 4326)::geography, :radius)
            ),
            routes_near_dest AS (
                SELECT DISTINCT p.id as pattern3_id, p.id_linea as linea3_id,
                       l3.short_name as short_name3, l3.nombre as linea3,
                       l3.color as color3, l3.text_color as text_color3
                FROM transporte.patterns p
                JOIN transporte.lineas l3 ON p.id_linea = l3.id_linea
                WHERE p.geometry IS NOT NULL AND l3.activa = true
                AND ST_DWithin(p.geometry::geography,
                    ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geography, :radius)
            ),
            middle_routes AS (
                SELECT DISTINCT p.id as pattern2_id, p.id_linea as linea2_id,
                       l2.short_name as short_name2, l2.nombre as linea2,
                       l2.color as color2, l2.text_color as text_color2
                FROM transporte.patterns p
                JOIN transporte.lineas l2 ON p.id_linea = l2.id_linea
                WHERE p.geometry IS NOT NULL AND l2.activa = true
            ),
            triple_combinations AS (
                SELECT 
                    ro.pattern1_id, ro.linea1, ro.short_name1, ro.color1, ro.text_color1,
                    mr.pattern2_id, mr.linea2, mr.short_name2, mr.color2, mr.text_color2,
                    rd.pattern3_id, rd.linea3, rd.short_name3, rd.color3, rd.text_color3,
                    ST_ClosestPoint(p1.geometry, p2.geometry) as transfer1_point,
                    ST_ClosestPoint(p2.geometry, p3.geometry) as transfer2_point
                FROM routes_near_origin ro
                JOIN middle_routes mr ON ro.linea1_id != mr.linea2_id
                JOIN routes_near_dest rd ON mr.linea2_id != rd.linea3_id AND ro.linea1_id != rd.linea3_id
                JOIN transporte.patterns p1 ON ro.pattern1_id = p1.id
                JOIN transporte.patterns p2 ON mr.pattern2_id = p2.id
                JOIN transporte.patterns p3 ON rd.pattern3_id = p3.id
                WHERE ST_DWithin(p1.geometry::geography, p2.geometry::geography, 500)
                AND ST_DWithin(p2.geometry::geography, p3.geometry::geography, 500)
            )
            SELECT 
                tc.*,
                ST_Y(tc.transfer1_point) as transfer1_lat,
                ST_X(tc.transfer1_point) as transfer1_lon,
                ST_Y(tc.transfer2_point) as transfer2_lat,
                ST_X(tc.transfer2_point) as transfer2_lon
            FROM triple_combinations tc
            LIMIT 50
        """)
        
        try:
            return db.execute(query, {
                "from_lat": from_lat, "from_lon": from_lon,
                "to_lat": to_lat, "to_lon": to_lon,
                "radius": radius
            }).fetchall()
        except Exception as e:
            print(f"[RoutePlanner] Error en _find_triple_transfer_routes: {e}")
            return []

    def _build_triple_transfer_itinerary(self, db: Session, route, from_lat, from_lon, to_lat, to_lon, start_time):
        """Construye itinerario con 2 transbordos (3 micros)"""
        try:
            # Obtener geometrías
            bus1_coords = self._get_pattern_geometry(db, route.pattern1_id)
            bus2_coords = self._get_pattern_geometry(db, route.pattern2_id)
            bus3_coords = self._get_pattern_geometry(db, route.pattern3_id)
            
            if not all([bus1_coords, bus2_coords, bus3_coords]):
                return None
            
            # Encontrar puntos en cada línea
            origin_point, o1 = self._find_closest_point_on_line(bus1_coords, from_lat, from_lon)
            t1_1, t1_1_idx = self._find_closest_point_on_line(bus1_coords, float(route.transfer1_lat), float(route.transfer1_lon))
            t1_2, t1_2_idx = self._find_closest_point_on_line(bus2_coords, float(route.transfer1_lat), float(route.transfer1_lon))
            t2_1, t2_1_idx = self._find_closest_point_on_line(bus2_coords, float(route.transfer2_lat), float(route.transfer2_lon))
            t2_2, t2_2_idx = self._find_closest_point_on_line(bus3_coords, float(route.transfer2_lat), float(route.transfer2_lon))
            dest_point, d3 = self._find_closest_point_on_line(bus3_coords, to_lat, to_lon)
            
            # Validar orden
            if o1 >= t1_1_idx or t1_2_idx >= t2_1_idx or t2_2_idx >= d3:
                return None
            
            # Calcular caminata total (siguiendo calles)
            walk_total = (
                walking_distance_realistic(from_lat, from_lon, origin_point[0], origin_point[1]) +
                walking_distance_realistic(t1_1[0], t1_1[1], t1_2[0], t1_2[1]) +
                walking_distance_realistic(t2_1[0], t2_1[1], t2_2[0], t2_2[1]) +
                walking_distance_realistic(dest_point[0], dest_point[1], to_lat, to_lon)
            )
            
            if walk_total > 800:  # Máximo 800m para 3 micros
                return None
            
            legs = []
            current_time = start_time
            total_walk = 0
            total_transit = 0
            total_wait = 0
            
            # Leg 1: Caminar a primera línea (siguiendo calles)
            w1 = walking_distance_realistic(from_lat, from_lon, origin_point[0], origin_point[1])
            wt1 = self._calculate_walk_time(w1)
            legs.append(LegSchema(mode="WALK", startTime=current_time,
                endTime=current_time + wt1*1000, duration=float(wt1), distance=w1,
                from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
                to=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding"),
                legGeometry=LegGeometry(points=encode_polyline([(from_lat, from_lon), origin_point]), length=2)))
            current_time += wt1*1000
            total_walk += w1
            
            # Espera bus 1
            wait1 = WAIT_TIME_MINUTES * 60
            current_time += wait1*1000
            total_wait += wait1
            
            # Leg 2: Bus 1 hasta transbordo 1
            seg1 = bus1_coords[o1:t1_1_idx+1]
            d1 = sum(haversine_distance(seg1[i][0], seg1[i][1], seg1[i+1][0], seg1[i+1][1]) for i in range(len(seg1)-1))
            t1 = self._calculate_bus_time(d1)
            legs.append(LegSchema(mode="BUS", startTime=current_time, endTime=current_time + t1*1000,
                duration=float(t1), distance=d1, from_=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding"),
                to=PlaceSchema(lat=t1_1[0], lon=t1_1[1], name="Transfer 1"),
                route=route.linea1, routeId=route.pattern1_id, routeShortName=route.short_name1,
                routeColor=route.color1 or "0088FF", routeTextColor=route.text_color1 or "FFFFFF",
                legGeometry=LegGeometry(points=encode_polyline(seg1), length=len(seg1)), transitLeg=True))
            current_time += t1*1000
            total_transit += t1
            
            # Leg 3: Caminar entre transbordo 1 (siguiendo calles)
            w2 = walking_distance_realistic(t1_1[0], t1_1[1], t1_2[0], t1_2[1])
            wt2 = self._calculate_walk_time(w2)
            legs.append(LegSchema(mode="WALK", startTime=current_time, endTime=current_time + wt2*1000,
                duration=float(wt2), distance=w2, from_=PlaceSchema(lat=t1_1[0], lon=t1_1[1], name="Transfer 1"),
                to=PlaceSchema(lat=t1_2[0], lon=t1_2[1], name="Transfer 1"),
                legGeometry=LegGeometry(points=encode_polyline([t1_1, t1_2]), length=2)))
            current_time += wt2*1000
            total_walk += w2
            
            # Espera bus 2
            wait2 = WAIT_TIME_MINUTES * 60
            current_time += wait2*1000
            total_wait += wait2
            
            # Leg 4: Bus 2 hasta transbordo 2
            seg2 = bus2_coords[t1_2_idx:t2_1_idx+1]
            d2 = sum(haversine_distance(seg2[i][0], seg2[i][1], seg2[i+1][0], seg2[i+1][1]) for i in range(len(seg2)-1))
            t2 = self._calculate_bus_time(d2)
            legs.append(LegSchema(mode="BUS", startTime=current_time, endTime=current_time + t2*1000,
                duration=float(t2), distance=d2, from_=PlaceSchema(lat=t1_2[0], lon=t1_2[1], name="Transfer 1"),
                to=PlaceSchema(lat=t2_1[0], lon=t2_1[1], name="Transfer 2"),
                route=route.linea2, routeId=route.pattern2_id, routeShortName=route.short_name2,
                routeColor=route.color2 or "FF5722", routeTextColor=route.text_color2 or "FFFFFF",
                legGeometry=LegGeometry(points=encode_polyline(seg2), length=len(seg2)), transitLeg=True))
            current_time += t2*1000
            total_transit += t2
            
            # Leg 5: Caminar entre transbordo 2 (siguiendo calles)
            w3 = walking_distance_realistic(t2_1[0], t2_1[1], t2_2[0], t2_2[1])
            wt3 = self._calculate_walk_time(w3)
            legs.append(LegSchema(mode="WALK", startTime=current_time, endTime=current_time + wt3*1000,
                duration=float(wt3), distance=w3, from_=PlaceSchema(lat=t2_1[0], lon=t2_1[1], name="Transfer 2"),
                to=PlaceSchema(lat=t2_2[0], lon=t2_2[1], name="Transfer 2"),
                legGeometry=LegGeometry(points=encode_polyline([t2_1, t2_2]), length=2)))
            current_time += wt3*1000
            total_walk += w3
            
            # Espera bus 3
            wait3 = WAIT_TIME_MINUTES * 60
            current_time += wait3*1000
            total_wait += wait3
            
            # Leg 6: Bus 3 hasta destino
            seg3 = bus3_coords[t2_2_idx:d3+1]
            d3_dist = sum(haversine_distance(seg3[i][0], seg3[i][1], seg3[i+1][0], seg3[i+1][1]) for i in range(len(seg3)-1))
            t3 = self._calculate_bus_time(d3_dist)
            legs.append(LegSchema(mode="BUS", startTime=current_time, endTime=current_time + t3*1000,
                duration=float(t3), distance=d3_dist, from_=PlaceSchema(lat=t2_2[0], lon=t2_2[1], name="Transfer 2"),
                to=PlaceSchema(lat=dest_point[0], lon=dest_point[1], name="Bus alighting"),
                route=route.linea3, routeId=route.pattern3_id, routeShortName=route.short_name3,
                routeColor=route.color3 or "4CAF50", routeTextColor=route.text_color3 or "FFFFFF",
                legGeometry=LegGeometry(points=encode_polyline(seg3), length=len(seg3)), transitLeg=True))
            current_time += t3*1000
            total_transit += t3
            
            # Leg 7: Caminar al destino (siguiendo calles)
            w4 = walking_distance_realistic(dest_point[0], dest_point[1], to_lat, to_lon)
            wt4 = self._calculate_walk_time(w4)
            legs.append(LegSchema(mode="WALK", startTime=current_time, endTime=current_time + wt4*1000,
                duration=float(wt4), distance=w4, from_=PlaceSchema(lat=dest_point[0], lon=dest_point[1], name="Bus alighting"),
                to=PlaceSchema(lat=to_lat, lon=to_lon, name="Destination"),
                legGeometry=LegGeometry(points=encode_polyline([dest_point, (to_lat, to_lon)]), length=2)))
            current_time += wt4*1000
            total_walk += w4
            
            return ItinerarySchema(legs=legs, startTime=start_time, endTime=current_time,
                duration=(current_time-start_time)//1000, walkTime=sum([wt1,wt2,wt3,wt4]),
                walkDistance=walk_total, transfers=2, transitTime=total_transit, waitingTime=total_wait)
        except Exception as e:
            print(f"[RoutePlanner] Error en _build_triple_transfer_itinerary: {e}")
            return None

    def _find_quadruple_transfer_routes(self, db: Session, from_lat: float, from_lon: float,
                                       to_lat: float, to_lon: float, radius: int = 1500):
        """Encuentra rutas con 3 transbordos (4 micros) - Solo para casos extremos"""
        # Similar a triple pero con una línea más
        # Por ahora retornar vacío - implementar solo si es necesario
        return []

    def _build_quadruple_transfer_itinerary(self, db: Session, route, from_lat, from_lon, to_lat, to_lon, start_time):
        """Construye itinerario con 3 transbordos (4 micros) - Solo para casos extremos"""
        # Por ahora retornar None - implementar solo si es necesario
        return None

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
            LIMIT 60
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

        # VALIDACIÓN: Rechazar si caminata total > 1.2km (siguiendo calles)
        walk_to_stop = walking_distance_realistic(from_lat, from_lon, float(origin_stop.latitud), float(origin_stop.longitud))
        walk_from_stop = walking_distance_realistic(float(dest_stop.latitud), float(dest_stop.longitud), to_lat, to_lon)
        
        if walk_to_stop + walk_from_stop > 1200:
            return None

        legs = []
        current_time = start_time
        total_walk_time = 0
        total_walk_dist = 0
        
        # Leg 1: Caminar a la parada
        walk_dist1 = walk_to_stop
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
        walk_dist2 = walking_distance_realistic(float(dest_stop.latitud), float(dest_stop.longitud), to_lat, to_lon)
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
        bus_coords = self._get_pattern_geometry(db, route.pattern_id)
        if not bus_coords or len(bus_coords) < 2:
            return None
        
        # Encontrar el punto más cercano al origen y destino en el trazado
        origin_point, origin_idx = self._find_closest_point_on_line(bus_coords, from_lat, from_lon)
        dest_point, dest_idx = self._find_closest_point_on_line(bus_coords, to_lat, to_lon)
        
        # Leg 1: Caminar al punto de abordaje (siguiendo calles)
        walk_dist1 = walking_distance_realistic(from_lat, from_lon, origin_point[0], origin_point[1])
        walk_time1 = self._calculate_walk_time(walk_dist1)
        
        walk_coords1 = [(from_lat, from_lon), origin_point]
        legs.append(LegSchema(
            mode="WALK",
            startTime=current_time,
            endTime=current_time + (walk_time1 * 1000),
            duration=float(walk_time1),
            distance=walk_dist1,
            from_=PlaceSchema(lat=from_lat, lon=from_lon, name="Origin"),
            to=PlaceSchema(lat=origin_point[0], lon=origin_point[1], name="Bus boarding"),
            legGeometry=LegGeometry(points=encode_polyline(walk_coords1), length=len(walk_coords1))
        ))
        current_time += walk_time1 * 1000
        total_walk_time += walk_time1
        total_walk_dist += walk_dist1
        
        # Tiempo de espera
        wait_time = WAIT_TIME_MINUTES * 60
        current_time += wait_time * 1000
        
        # Leg 2: Viaje en bus
        if origin_idx >= dest_idx:
            # Lógica para Rutas Circulares (Wrap-around)
            is_loop = False
            if len(bus_coords) > 10:
                first_p = bus_coords[0]
                last_p = bus_coords[-1]
                dist_ends = haversine_distance(first_p[0], first_p[1], last_p[0], last_p[1])
                if dist_ends < 1000:  # Aumentado de 500 a 1000m para detectar más loops
                    is_loop = True
            
            if is_loop:
                route_segment_1 = bus_coords[origin_idx:]
                route_segment_2 = bus_coords[:dest_idx+1]
                route_segment = route_segment_1 + route_segment_2
            else:
                # CAMBIO: Si no es loop, verificar si el destino está "atrás" por poco
                # En ese caso, invertir y usar solo la sección necesaria
                if origin_idx - dest_idx < 10:  # Diferencia pequeña
                    # Usar ruta corta al revés
                    route_segment = bus_coords[dest_idx:origin_idx+1]
                    route_segment.reverse()
                else:
                    return None  # Ruta no válida
        else:
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
        
        # Leg 3: Caminar al destino final (siguiendo calles)
        walk_dist2 = walking_distance_realistic(dest_point[0], dest_point[1], to_lat, to_lon)
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
        if not coords:
            return (lat, lon), 0
            
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

        # VALIDACIÓN CRÍTICA: Rechazar si la caminata inicial es excesiva (siguiendo calles)
        walk_to_first_stop = walking_distance_realistic(from_lat, from_lon, float(origin_stop.latitud), float(origin_stop.longitud))
        walk_from_last_stop = walking_distance_realistic(float(dest_stop.latitud), float(dest_stop.longitud), to_lat, to_lon)
        total_walk_estimate = walk_to_first_stop + walk_from_last_stop
        
        # Si la caminata total es > 1.5km, rechazar este transbordo
        if total_walk_estimate > 1500:
            return None

        legs = []
        current_time = start_time
        total_walk_time = 0
        total_walk_dist = 0
        total_transit_time = 0
        total_wait_time = 0
        
        # Leg 1: Caminar a la primera parada
        walk_dist1 = walk_to_first_stop
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
        
        # Leg 4: Caminar al destino (siguiendo calles)
        walk_dist2 = walking_distance_realistic(float(dest_stop.latitud), float(dest_stop.longitud), to_lat, to_lon)
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
        distance = walking_distance_realistic(from_lat, from_lon, to_lat, to_lon)
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
