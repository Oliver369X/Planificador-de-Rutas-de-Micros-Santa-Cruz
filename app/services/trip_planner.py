from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models import Route, Stop, Line, Trip, Transfer
from math import radians, sin, cos, sqrt, atan2
from app.schemas.trip import TripResponse

class TripPlanner:
    """Servicio para planificación de viajes y cálculo de rutas óptimas."""
    
    EARTH_RADIUS_KM = 6371.0
    MAX_TRANSFER_DISTANCE_KM = 0.5  # Distancia máxima a pie entre paradas
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia en km entre dos coordenadas."""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return TripPlanner.EARTH_RADIUS_KM * c
    
    @classmethod
    def find_nearest_stops(
        cls,
        db: Session,
        lat: float,
        lon: float,
        max_distance_km: float = 0.3
    ) -> List[Stop]:
        """Encuentra paradas cercanas a un punto."""
        stops = db.query(Stop).filter(Stop.activa == True).all()
        nearby = []
        for stop in stops:
            dist = cls.haversine_distance(lat, lon, float(stop.latitud), float(stop.longitud))
            if dist <= max_distance_km:
                nearby.append((stop, dist))
        return sorted(nearby, key=lambda x: x[1])
    
    @classmethod
    def plan_trip(
        cls,
        db: Session,
        user_id: int,
        origen_lat: float,
        origen_lon: float,
        destino_lat: float,
        destino_lon: float
    ) -> Dict:
        """
        Planifica un viaje desde origen a destino.
        Retorna múltiples alternativas ordenadas por tiempo.
        """
        # Encontrar paradas cercanas al origen y destino
        nearby_origin = cls.find_nearest_stops(db, origen_lat, origen_lon)
        nearby_destination = cls.find_nearest_stops(db, destino_lat, destino_lon)
        
        if not nearby_origin or not nearby_destination:
            return {"error": "No se encontraron paradas cercanas al origen o destino"}
        
        alternatives = []
        
        # Generar planes de viaje (simplificado: búsqueda directa sin trasbordo primero)
        for start_stop, start_dist in nearby_origin[:3]:
            for end_stop, end_dist in nearby_destination[:3]:
                # Buscar líneas que pasen por ambas paradas en orden correcto
                routes = db.query(Route).filter(
                    and_(
                        Route.id_parada == start_stop.id_parada,
                        Route.sentido == 'ida',
                        Route.linea.has(Line.activa == True)
                    )
                ).all()
                
                for route_start in routes:
                    # Verificar si la línea llega a la parada destino
                    route_end = db.query(Route).filter(
                        and_(
                            Route.id_linea == route_start.id_linea,
                            Route.id_parada == end_stop.id_parada,
                            Route.sentido == 'ida',
                            Route.orden > route_start.orden
                        )
                    ).first()
                    
                    if route_end:
                        # Calcular tiempo total
                        tiempo_total = (route_end.tiempo_estimado or 0) + int(start_dist * 5) + int(end_dist * 5)
                        distancia_total = cls.haversine_distance(
                            origen_lat, origen_lon, destino_lat, destino_lon
                        )
                        
                        alternatives.append({
                            "lineas": [route_start.linea.nombre],
                            "tiempo_estimado": tiempo_total,
                            "distancia": distancia_total,
                            "trasbordos": 0,
                            "parada_inicio": start_stop.nombre,
                            "parada_fin": end_stop.nombre
                        })
        
        # Ordenar por tiempo estimado
        alternatives = sorted(alternatives, key=lambda x: x['tiempo_estimado'])
        
        return {
            "origen": {"lat": origen_lat, "lon": origen_lon},
            "destino": {"lat": destino_lat, "lon": destino_lon},
            "alternativas": alternatives[:5]  # Top 5 opciones
        }
