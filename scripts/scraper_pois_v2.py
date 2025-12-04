"""
Scraper Completo de POIs - Versión mejorada con formatos reales
Scrapea: Educación, Salud, Deportes, Abastecimiento, Transporte
"""

import asyncio
import httpx
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

GUIA_URBANA_BASE = "https://guiaurbana.gmsantacruz.gob.bo/guiaurbana/public/api"

# Configuración de endpoints basada en ejemplos reales
POI_ENDPOINTS = {
    "educacion": {
        "endpoints": [
            {"path": "/educacion/20", "subtipo": "locales_educativos"},
            {"path": "/educacion/14", "subtipo": "universidades"},
        ],
        "tipo": "educacion"
    },
    "salud": {
        "endpoints": [
            {"path": "/salud/20.1", "subtipo": "hospitales"},
            {"path": "/salud/DEPARTAMENTAL", "subtipo": "hospitales_departamentales"},
        ],
        "tipo": "salud"
    },
    "deportes": {
        "endpoints": [
            {"path": "/deportes/55", "subtipo": "balnearios_piscinas"},
            {"path": "/deportes/52", "subtipo": "otros_deportes"},
        ],
        "tipo": "deportes"
    },
    "abastecimiento": {
        "endpoints": [
            {"path": "/abastecimiento/74", "subtipo": "centros_comerciales"},
        ],
        "tipo": "abastecimiento"
    },
    "transporte": {
        "endpoints": [
            {"path": "/transporte/90", "subtipo": "oficinas_linea_micro"},
        ],
        "tipo": "transporte"
    }
}

class POIScraperV2:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.stats = {
            "total_insertados": 0,
            "por_tipo": {},
            "errores": []
        }
        
        for tipo in POI_ENDPOINTS.keys():
            self.stats["por_tipo"][tipo] = {"ok": 0, "fail": 0}
    
    async def fetch(self, url):
        """Fetch data from URL"""
        try:
            r = await self.client.get(url)
            if r.status_code == 200:
                data = r.json()
                # API devuelve lista directamente
                if isinstance(data, list):
                    return data
            return []
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return []
    
    def insert_poi(self, tipo, subtipo, item):
        """Inserta un POI en la base de datos"""
        try:
            # Extraer coordenadas (x = lon, y = lat)
            lon = item.get("x")
            lat = item.get("y")
            
            if not lon or not lat:
                return False
            
            # Limpiar coordenadas (pueden venir como string)
            try:
                lon = float(str(lon).strip())
                lat = float(str(lat).strip())
            except:
                return False
            
            # Generar objectid único si no existe
            objectid = item.get("objectid")
            if not objectid:
                # Usar hash del nombre + coordenadas
                objectid = hash(f"{item.get('nombre', 'unknown')}_{lat}_{lon}") % (10 ** 8)
            
            nombre = item.get("nombre", "Sin nombre")
            if not nombre or nombre.strip() == "":
                nombre = "Sin nombre"
            
            # Preparar metadata JSON
            metadata_dict = {
                "sistema": item.get("sistema"),
                "sub_sistem": item.get("sub_sistem"),
                "nivel": item.get("nivel"),
                "uv": item.get("uv"),
                "mz": item.get("mz"),
                "infraestru": item.get("infraestru"),
                "adm_infrae": item.get("adm_infrae"),
                "red_de_sal": item.get("red_de_sal"),
            }
            
            # Queries con upsert (ON CONFLICT UPDATE)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO transporte.points_of_interest 
                    (objectid, nombre, tipo, subtipo, latitud, longitud, geom, 
                     direccion, telefono, horario, distrito, metadata)
                    VALUES 
                    (:objectid, :nombre, :tipo, :subtipo, :lat, :lon, 
                     ST_SetSRID(ST_MakePoint(:lon_geom, :lat_geom), 4326),
                     :direccion, :telefono, :horario, :distrito, CAST(:metadata_json AS jsonb))
                    ON CONFLICT (objectid) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        direccion = EXCLUDED.direccion,
                        metadata = EXCLUDED.metadata
                """), {
                    "objectid": int(objectid),
                    "nombre": nombre[:255],
                    "tipo": tipo,
                    "subtipo": subtipo,
                    "lat": str(lat),
                    "lon": str(lon),
                    "lon_geom": lon,
                    "lat_geom": lat,
                    "direccion": item.get("direccion"),
                    "telefono": None,  # No está en estos endpoints
                    "horario": None,
                    "distrito": str(item.get("distrito", "")),
                    "metadata_json": json.dumps(metadata_dict)
                })
                conn.commit()
            
            self.stats["total_insertados"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error insertando POI: {e}")
            self.stats["errores"].append(str(e))
            return False
    
    async def scrape_endpoint(self, tipo, endpoint_config):
        """Scrapea un endpoint específico"""
        path = endpoint_config["path"]
        subtipo = endpoint_config["subtipo"]
        
        url = f"{GUIA_URBANA_BASE}{path}"
        logger.info(f"  📡 Fetching {tipo}/{subtipo}...")
        
        items = await self.fetch(url)
        
        if not items:
            logger.warning(f"    ⚠️  Sin datos")
            return
        
        count = 0
        for item in items:
            if self.insert_poi(tipo, subtipo, item):
                count += 1
        
        self.stats["por_tipo"][tipo]["ok"] += count
        logger.info(f"    ✅ {count} POIs guardados")
    
    async def scrape_category(self, tipo, config):
        """Scrapea una categoría completa"""
        logger.info(f"\n🔍 {tipo.upper()}...")
        
        for endpoint_config in config["endpoints"]:
            await self.scrape_endpoint(tipo, endpoint_config)
            await asyncio.sleep(0.1)  # Pausa entre requests
    
    async def run(self):
        """Ejecuta el scraping completo"""
        logger.info("=" * 70)
        logger.info("🚀 SCRAPING POIs - Versión 2.0")
        logger.info("=" * 70)
        
        for tipo, config in POI_ENDPOINTS.items():
            await self.scrape_category(tipo, config)
        
        await self.client.aclose()
        
        # Reporte final
        self.print_report()
    
    def print_report(self):
        """Reporte final"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 REPORTE FINAL")
        logger.info("=" * 70)
        
        for tipo, stats in self.stats["por_tipo"].items():
            logger.info(f"{tipo:20} → ✅ {stats['ok']:4} POIs")
        
        logger.info(f"\n🎯 TOTAL INSERTADOS: {self.stats['total_insertados']}")
        
        if self.stats["errores"]:
            logger.info(f"\n❌ Errores: {len(self.stats['errores'])}")
        
        # Verificar en BD
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM transporte.points_of_interest"))
            total = result.fetchone()[0]
            logger.info(f"\n📍 Total POIs en base de datos: {total}")
            
            # Por tipo
            result = conn.execute(text("""
                SELECT tipo, COUNT(*) as total
                FROM transporte.points_of_interest
                GROUP BY tipo
                ORDER BY total DESC
            """))
            logger.info("\n📊 Distribución por tipo:")
            for row in result:
                logger.info(f"  {row[0]:20} : {row[1]:4} POIs")
        
        logger.info("=" * 70)

async def main():
    logger.info("\n🔧 Inicializando scraper de POIs v2.0...")
    
    scraper = POIScraperV2()
    await scraper.run()
    
    logger.info("\n✅ Scraping completado")

if __name__ == "__main__":
    asyncio.run(main())
