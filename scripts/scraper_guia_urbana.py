"""
Script de Web Scraping - Guía Urbana Municipal Santa Cruz
Extrae datos de 132 líneas de micros y los almacena en el backend
"""

import asyncio
import httpx
import sys
import os
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point
import logging

# Agregar path del backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.line import Line
from app.models.stop import Stop
from app.models.pattern import Pattern
from app.models.pattern_stop import PatternStop

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración
GUIA_URBANA_BASE = "https://guiaurbana.gmsantacruz.gob.bo/guiaurbana/public/api"
MAX_ROUTE_ID = 132  # 132 líneas de micros en Santa Cruz
BATCH_SIZE = 10   # Requests concurrentes
STOP_INTERVAL = 5  # Puntos de intervalo para generar paradas

class GuiaUrbanaScraper:
    """Scraper para API Guía Urbana Municipal"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=20.0)
        self.stats = {
            "rutas_exitosas": 0,
            "rutas_fallidas": 0,
            "lineas_creadas": 0,
            "patterns_creados": 0,
            "paradas_creadas": 0,
            "errores": []
        }
    
    async def fetch_ruta(self, ruta_id: int) -> Optional[Dict]:
        """
        Obtiene datos de una ruta desde la API municipal
        
        Args:
            ruta_id: ID de la ruta (1-132)
            
        Returns:
            GeoJSON FeatureCollection o None si falla
        """
        url = f"{GUIA_URBANA_BASE}/rutaMicrobuses/{ruta_id}"
        
        try:
            logger.debug(f"  Fetching {url}")
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # La API devuelve una lista con un dict dentro
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
            elif response.status_code == 404:
                logger.debug(f"  Ruta {ruta_id} no existe (404)")
                return None
            else:
                logger.warning(f"  Error {response.status_code} para ruta {ruta_id}")
                return None
                
        except httpx.TimeoutException:
            logger.error(f"  Timeout al obtener ruta {ruta_id}")
            self.stats["errores"].append(f"Ruta {ruta_id}: Timeout")
            return None
        except Exception as e:
            logger.error(f"  Excepción al obtener ruta {ruta_id}: {e}")
            self.stats["errores"].append(f"Ruta {ruta_id}: {str(e)}")
            return None
    
    def extract_routes_from_geojson(self, geojson_data: Dict) -> List[Dict]:
        """Extrae información de Features del GeoJSON"""
        routes = []
        
        # Validar que el dato no sea None
        if not geojson_data:
            return routes
        
        # Validar que sea un dict
        if not isinstance(geojson_data, dict):
            return routes
            
        # Validar que tenga features  
        if "features" not in geojson_data:
            return routes
        
        # Validar que features no sea None
        features = geojson_data.get("features")
        if features is None:
            return routes
        
        for feature in features:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            
            route_info = {
                "nombre": props.get("nombre", ""),
                "sentido": props.get("sentido", 1),
                "origen": props.get("origen"),
                "destino": props.get("destino"),
                "sindicato": props.get("sindicato"),
                "geometry": geom,
                "objectid": feature.get("id") or props.get("objectid")
            }
            
            routes.append(route_info)
        
        return routes
    
    def create_or_get_line(self, nombre: str) -> Line:
        """Crea o retorna línea existente"""
        line = self.db.query(Line).filter(Line.nombre == nombre).first()
        
        if not line:
            line = Line(
                nombre=nombre,
                short_name=nombre,
                long_name=f"Línea {nombre}",
                color="0088FF",
                text_color="FFFFFF",
                mode="BUS",
                activa=True
            )
            self.db.add(line)
            self.db.commit()
            self.db.refresh(line)
            self.stats["lineas_creadas"] += 1
            logger.info(f"    ✅ Línea creada: {nombre}")
        
        return line
    
    def create_pattern(
        self,
        line: Line,
        nombre_ruta: str,
        sentido: int,
        geometry: Dict,
        objectid: int
    ) -> Optional[Pattern]:
        """Crea un pattern (patrón de ruta)"""
        sentido_str = "ida" if sentido == 1 else "vuelta"
        pattern_id = f"pattern:{line.id_linea}:{sentido_str}"
        
        # Eliminar si existe (reemplazar)
        existing = self.db.query(Pattern).filter(Pattern.id == pattern_id).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()
        
        # Convertir geometría GeoJSON a LineString PostGIS
        geom_obj = self.convert_geometry_to_linestring(geometry)
        
        if not geom_obj:
            logger.warning(f"    ⚠️  Pattern {pattern_id}: geometría inválida")
            return None
        
        pattern = Pattern(
            id=pattern_id,
            code=nombre_ruta,
            name=f"{nombre_ruta} - {sentido_str.capitalize()}",
            id_linea=line.id_linea,
            sentido=sentido_str,
            geometry=geom_obj
        )
        
        self.db.add(pattern)
        self.db.commit()
        self.db.refresh(pattern)
        
        self.stats["patterns_creados"] += 1
        logger.info(f"    ✅ Pattern: {pattern.name}")
        
        return pattern
    
    def convert_geometry_to_linestring(self, geometry: Dict) -> Optional:
        """Convierte GeoJSON MultiLineString a LineString PostGIS"""
        if not geometry or geometry.get("type") != "MultiLineString":
            return None
        
        try:
            # Flatten MultiLineString a LineString
            coords = []
            for line_coords in geometry.get("coordinates", []):
                coords.extend(line_coords)
            
            if not coords:
                return None
            
            line_geom = LineString(coords)
            return from_shape(line_geom, srid=4326)
            
        except Exception as e:
            logger.error(f"Error convirtiendo geometría: {e}")
            return None
    
    def extract_stops_from_geometry(self, pattern: Pattern, geometry: Dict):
        """
        Extrae paradas estimadas de la geometría de la ruta
        Toma puntos a intervalos regulares de la línea
        """
        if not geometry or geometry.get("type") != "MultiLineString":
            return
        
        # Aplanar coordenadas
        coords = []
        for line_coords in geometry.get("coordinates", []):
            coords.extend(line_coords)
        
        if not coords:
            return
        
        # Generar paradas cada N puntos
        step = max(len(coords) // 20, 1)  # Aproximadamente 20 paradas por ruta
        sequence = 1
        
        for i in range(0, len(coords), step):
            lon, lat = coords[i]
            
            # Buscar parada cercana (150m) o crear nueva
            stop = self.find_or_create_stop(
                lat=lat,
                lon=lon,
                nombre=f"Parada {pattern.code} #{sequence}"
            )
            
            # Asociar con pattern
            pattern_stop = PatternStop(
                pattern_id=pattern.id,
                id_parada=stop.id_parada,
                sequence=sequence
            )
            self.db.add(pattern_stop)
            sequence += 1
        
        self.db.commit()
        logger.info(f"      📍 {sequence-1} paradas asociadas")
    
    def find_or_create_stop(self, lat: float, lon: float, nombre: str) -> Stop:
        """Encuentra parada cercana (<150m) o crea una nueva"""
        from sqlalchemy import text
        
        # Buscar parada dentro de 150m
        query = text("""
            SELECT id_parada 
            FROM transporte.paradas 
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                150
            )
            ORDER BY ST_Distance(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            )
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"lat": lat, "lon": lon}).fetchone()
        
        if result:
            return self.db.query(Stop).get(result[0])
        
        # Crear nueva parada
        point_geom = from_shape(Point(lon, lat), srid=4326)
        
        stop = Stop(
            nombre_parada=nombre,
            latitud=lat,
            longitud=lon,
            geom=point_geom,
            activa=True
        )
        self.db.add(stop)
        self.db.commit()
        self.db.refresh(stop)
        
        self.stats["paradas_creadas"] += 1
        return stop
    
    async def scrape_route(self, ruta_id: int):
        """Procesa una ruta completa"""
        logger.info(f"📥 Ruta {ruta_id}...")
        
        geojson = await self.fetch_ruta(ruta_id)
        
        if not geojson:
            self.stats["rutas_fallidas"] += 1
            return
        
        routes = self.extract_routes_from_geojson(geojson)
        
        if not routes:
            logger.warning(f"⚠️  Ruta {ruta_id} sin features")
            self.stats["rutas_fallidas"] += 1
            return
        
        try:
            # Procesar cada sentido (ida/vuelta)
            for route_data in routes:
                nombre = route_data["nombre"]
                
                if not nombre:
                    continue
                
                # Crear/obtener línea
                line = self.create_or_get_line(nombre)
                
                # Crear pattern
                pattern = self.create_pattern(
                    line=line,
                    nombre_ruta=nombre,
                    sentido=route_data["sentido"],
                    geometry=route_data["geometry"],
                    objectid=route_data["objectid"]
                )
                
                if pattern:
                    # Extraer paradas
                    self.extract_stops_from_geometry(pattern, route_data["geometry"])
            
            self.stats["rutas_exitosas"] += 1
            
        except Exception as e:
            logger.error(f"❌ Error procesando ruta {ruta_id}: {e}")
            self.stats["errores"].append(f"Ruta {ruta_id}: {str(e)}")
            self.stats["rutas_fallidas"] += 1
            self.db.rollback()
    
    async def scrape_all_routes(self):
        """Scrapea todas las 132 rutas en lotes"""
        logger.info("=" * 70)
        logger.info(f"🚀 INICIANDO SCRAPING DE {MAX_ROUTE_ID} LÍNEAS DE MICROS")
        logger.info("=" * 70)
        
        for i in range(1, MAX_ROUTE_ID + 1, BATCH_SIZE):
            batch = range(i, min(i + BATCH_SIZE, MAX_ROUTE_ID + 1))
            
            logger.info(f"\n📦 Lote {i}-{min(i+BATCH_SIZE-1, MAX_ROUTE_ID)}...")
            
            tasks = [self.scrape_route(ruta_id) for ruta_id in batch]
            await asyncio.gather(*tasks)
            
            # Pausa entre lotes para no sobrecargar servidor
            await asyncio.sleep(1)
        
        await self.client.aclose()
        
        # Reporte final
        self.print_report()
    
    def print_report(self):
        """Imprime reporte final de scraping"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 REPORTE FINAL DE SCRAPING")
        logger.info("=" * 70)
        logger.info(f"✅ Rutas exitosas:     {self.stats['rutas_exitosas']}")
        logger.info(f"❌ Rutas fallidas:     {self.stats['rutas_fallidas']}")
        logger.info(f"🚍 Líneas creadas:     {self.stats['lineas_creadas']}")
        logger.info(f"🛣️  Patterns creados:   {self.stats['patterns_creados']}")
        logger.info(f"📍 Paradas creadas:    {self.stats['paradas_creadas']}")
        
        if self.stats["errores"]:
            logger.info(f"\n⚠️  Errores ({len(self.stats['errores'])}):")
            for error in self.stats["errores"][:10]:  # Mostrar primeros 10
                logger.info(f"   - {error}")
        
        logger.info("=" * 70)
        
        # Resumen de BD
        total_lineas = self.db.query(Line).count()
        total_patterns = self.db.query(Pattern).count()
        total_paradas = self.db.query(Stop).count()
        
        logger.info("\n📊 DATOS EN BASE DE DATOS:")
        logger.info(f"   Total Líneas:   {total_lineas}")
        logger.info(f"   Total Patterns: {total_patterns}")
        logger.info(f"   Total Paradas:  {total_paradas}")
        logger.info("=" * 70)

async def main():
    """Función principal"""
    logger.info("\n🔧 Inicializando scraper...")
    logger.info(f"🌐 Base URL: {GUIA_URBANA_BASE}")
    logger.info(f"📊 Líneas a scrapear: 1-{MAX_ROUTE_ID}\n")
    
    db = SessionLocal()
    
    try:
        scraper = GuiaUrbanaScraper(db)
        await scraper.scrape_all_routes()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Scraping interrumpido por usuario")
    except Exception as e:
        logger.error(f"\n❌ Error fatal: {e}")
        raise
    finally:
        db.close()
        logger.info("\n✅ Scraper finalizado")

if __name__ == "__main__":
    asyncio.run(main())
