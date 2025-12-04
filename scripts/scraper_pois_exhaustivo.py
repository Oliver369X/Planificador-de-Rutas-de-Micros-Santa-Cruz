"""
Scraper EXHAUSTIVO de POIs - Versión 3.0
Prueba TODOS los IDs posibles incluyendo decimales
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

# Configuración EXHAUSTIVA - prueba TODOS los posibles IDs
ENDPOINTS_CONFIG = {
    "educacion": {
        "path": "/educacion",
        "tipo": "educacion",
        "ids_enteros": list(range(1, 150)),  # 1-150
        "ids_decimales": [f"{i}.{j}" for i in range(1, 50) for j in range(1, 5)],  # 1.1-49.4
        "subtipo": "educacion"
    },
    "salud": {
        "path": "/salud",
        "tipo": "salud",
        "ids_enteros": list(range(1, 100)),
        "ids_decimales": [f"{i}.{j}" for i in range(1, 50) for j in range(1, 5)],
        "subtipo": "salud"
    },
    "deportes": {
        "path": "/deportes",
        "tipo": "deportes",
        "ids_enteros": list(range(1, 150)),
        "ids_decimales": [f"{i}.{j}" for i in range(1, 50) for j in range(1, 5)],
        "subtipo": "deportes"
    },
    "abastecimiento": {
        "path": "/abastecimiento",
        "tipo": "abastecimiento",
        "ids_enteros": list(range(1, 150)),
        "ids_decimales": [f"{i}.{j}" for i in range(1, 50) for j in range(1, 5)],
        "subtipo": "comercial"
    },
    "transporte": {
        "path": "/transporte",
        "tipo": "transporte",
        "ids_enteros": list(range(1, 200)),  # Más rango para transporte
        "ids_decimales": [f"{i}.{j}" for i in range(1, 100) for j in range(1, 5)],
        "subtipo": "transporte"
    },
    "seguridad": {
        "path": "/seguridad",
        "tipo": "seguridad",
        "ids_enteros": list(range(1, 100)),
        "ids_decimales": [f"{i}.{j}" for i in range(1, 50) for j in range(1, 5)],
        "subtipo": "seguridad"
    }
}

class ExhaustivePOIScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.stats = {
            "total_requests": 0,
            "total_exitosos": 0,
            "total_insertados": 0,
            "por_tipo": {}
        }
        
        for tipo in ENDPOINTS_CONFIG.keys():
            self.stats["por_tipo"][tipo] = {"requests": 0, "exitosos": 0, "insertados": 0}
    
    async def fetch(self, url):
        """Fetch data from URL"""
        self.stats["total_requests"] += 1
        try:
            r = await self.client.get(url)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    self.stats["total_exitosos"] += 1
                    return data
            return []
        except Exception as e:
            return []
    
    def insert_poi(self, tipo, subtipo, item):
        """Inserta un POI en la base de datos"""
        try:
            lon = item.get("x")
            lat = item.get("y")
            
            if not lon or not lat:
                return False
            
            try:
                lon = float(str(lon).strip())
                lat = float(str(lat).strip())
            except:
                return False
            
            objectid = item.get("objectid")
            if not objectid:
                objectid = hash(f"{item.get('nombre', 'unknown')}_{lat}_{lon}") % (10 ** 8)
            
            nombre = item.get("nombre", "Sin nombre")
            if not nombre or nombre.strip() == "":
                nombre = "Sin nombre"
            
            metadata_dict = {
                "sistema": item.get("sistema"),
                "sub_sistem": item.get("sub_sistem"),
                "nivel": item.get("nivel"),
                "uv": item.get("uv"),
                "mz": item.get("mz"),
                "barrio": item.get("barrio"),
                "infraestru": item.get("infraestru"),
                "adm_infrae": item.get("adm_infrae"),
                "red_de_sal": item.get("red_de_sal"),
                "google_map": item.get("google_map"),
            }
            
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
                    "telefono": item.get("telefono"),
                    "horario": item.get("horario"),
                    "distrito": str(item.get("distrito", "")),
                    "metadata_json": json.dumps(metadata_dict)
                })
                conn.commit()
            
            self.stats["total_insertados"] += 1
            return True
            
        except Exception as e:
            return False
    
    async def scrape_id(self, tipo, config, id_value):
        """Scrapea un ID específico"""
        path = config["path"]
        subtipo = config["subtipo"]
        
        url = f"{GUIA_URBANA_BASE}{path}/{id_value}"
        
        self.stats["por_tipo"][tipo]["requests"] += 1
        
        items = await self.fetch(url)
        
        if items:
            self.stats["por_tipo"][tipo]["exitosos"] += 1
            count = 0
            for item in items:
                if self.insert_poi(tipo, subtipo, item):
                    count += 1
            
            self.stats["por_tipo"][tipo]["insertados"] += count
            if count > 0:
                logger.info(f"  ✅ {tipo}/{id_value}: {count} POIs")
            return count
        
        return 0
    
    async def scrape_category(self, tipo, config):
        """Scrapea una categoría completa"""
        logger.info(f"\n🔍 {tipo.upper()} - Modo EXHAUSTIVO")
        logger.info(f"  Probando {len(config['ids_enteros'])} IDs enteros + {len(config['ids_decimales'])} IDs decimales...")
        
        # Scrapear IDs enteros
        for id_val in config["ids_enteros"]:
            await self.scrape_id(tipo, config, id_val)
            await asyncio.sleep(0.05)  # Pausa corta
        
        # Scrapear IDs decimales
        for id_val in config["ids_decimales"]:
            await self.scrape_id(tipo, config, id_val)
            await asyncio.sleep(0.05)
        
        stats = self.stats["por_tipo"][tipo]
        logger.info(f"  📊 {tipo}: {stats['requests']} requests → {stats['exitosos']} exitosos → {stats['insertados']} insertados")
    
    async def run(self):
        """Ejecuta el scraping completo"""
        logger.info("=" * 70)
        logger.info("🚀 SCRAPING EXHAUSTIVO DE POIs - v3.0")
        logger.info("=" * 70)
        
        for tipo, config in ENDPOINTS_CONFIG.items():
            await self.scrape_category(tipo, config)
        
        await self.client.aclose()
        
        self.print_report()
    
    def print_report(self):
        """Reporte final"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 REPORTE FINAL EXHAUSTIVO")
        logger.info("=" * 70)
        
        logger.info(f"\n🌐 Total Requests: {self.stats['total_requests']}")
        logger.info(f"✅ Requests Exitosos: {self.stats['total_exitosos']}")
        logger.info(f"💾 POIs Insertados: {self.stats['total_insertados']}")
        
        logger.info("\n📋 Por Tipo:")
        for tipo, stats in self.stats["por_tipo"].items():
            logger.info(f"  {tipo:20} → {stats['requests']:4} req | {stats['exitosos']:3} ok | {stats['insertados']:4} POIs")
        
        # Verificar en BD
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM transporte.points_of_interest"))
            total = result.fetchone()[0]
            logger.info(f"\n📍 Total POIs en BD: {total}")
            
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
    logger.info("\n🔧 Scraper EXHAUSTIVO de POIs v3.0...")
    logger.info("⚠️  ADVERTENCIA: Esto hará ~2000+ requests (puede tardar 10-15 min)")
    
    scraper = ExhaustivePOIScraper()
    await scraper.run()
    
    logger.info("\n✅ Scraping EXHAUSTIVO completado")

if __name__ == "__main__":
    asyncio.run(main())
