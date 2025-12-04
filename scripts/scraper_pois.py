"""
Scraper POIs Simplificado - Sin usar modelo SQLAlchemy
"""

import asyncio
import httpx
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

GUIA_URBANA_BASE = "https://guiaurbana.gmsantacruz.gob.bo/guiaurbana/public/api"

POI_ENDPOINTS = {
    "salud": {"path": "/salud", "range": range(1, 50)},
    "seguridad": {"path": "/seguridad", "range": range(1, 50)},
    "educacion": {"path": "/educacion", "range": range(1, 50)},
    "transporte": {"path": "/transporte", "range": range(1, 100)}
}

class POIScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.stats = {k: {"ok": 0, "fail": 0} for k in POI_ENDPOINTS.keys()}
        self.total = 0
    
    async def fetch(self, url):
        try:
            r = await self.client.get(url)
            if r.status_code == 200:
                data = r.json()
                return data[0] if isinstance(data, list) and len(data) > 0 else data
        except:
            pass
        return None
    
    def insert_poi(self, tipo, feature):
        if not feature or feature.get("type") != "Feature":
            return False
        
        geom = feature.get("geometry", {})
        props = feature.get("properties", {})
        
        if geom.get("type") != "Point":
            return False
        
        coords = geom.get("coordinates", [])
        if len(coords) != 2:
            return False
        
        lon, lat = coords
        
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO transporte.points_of_interest 
                    (objectid, nombre, tipo, subtipo, latitud, longitud, geom, direccion, telefono, horario, distrito, metadata)
                    VALUES (:objectid, :nombre, :tipo, :subtipo, :lat, :lon, 
                            ST_SetSRID(ST_MakePoint(:lon_geom, :lat_geom), 4326),
                            :direccion, :telefono, :horario, :distrito, :metadata::jsonb)
                    ON CONFLICT (objectid) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        direccion = EXCLUDED.direccion,
                        telefono = EXCLUDED.telefono
                """), {
                    "objectid": props.get("objectid"),
                    "nombre": props.get("nombre", "Sin nombre"),
                    "tipo": tipo,
                    "subtipo": props.get("tipo"),
                    "lat": str(lat),
                    "lon": str(lon),
                    "lon_geom": lon,
                    "lat_geom": lat,
                    "direccion": props.get("direccion"),
                    "telefono": props.get("telefono"),
                    "horario": props.get("horario"),
                    "distrito": str(props.get("distrito", "")),
                    "metadata": str(props).replace("'", '"')
                })
                conn.commit()
            
            self.total += 1
            return True
        except Exception as e:
            logger.error(f"Error insertando: {e}")
            return False
    
    async def scrape_category(self, categoria, config):
        logger.info(f"\n🔍 {categoria.upper()}...")
        
        for poi_id in config["range"]:
            url = f"{GUIA_URBANA_BASE}{config['path']}/{poi_id}"
            feature = await self.fetch(url)
            
            if feature:
                success = self.insert_poi(categoria, feature)
                if success:
                    self.stats[categoria]["ok"] += 1
                    logger.info(f"  ✅ {categoria}: {feature.get('properties', {}).get('nombre', 'N/A')}")
                else:
                    self.stats[categoria]["fail"] += 1
            else:
                self.stats[categoria]["fail"] += 1
            
            await asyncio.sleep(0.05)
        
        logger.info(f"✅ {categoria}: {self.stats[categoria]['ok']} POIs")
    
    async def run(self):
        logger.info("🚀 SCRAPING POIs")
        logger.info("=" * 70)
        
        for cat, cfg in POI_ENDPOINTS.items():
            await self.scrape_category(cat, cfg)
        
        await self.client.aclose()
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMEN FINAL")
        for tipo, stats in self.stats.items():
            logger.info(f"{tipo:15} → ✅ {stats['ok']:3} | ❌ {stats['fail']:3}")
        logger.info(f"\n🎯 TOTAL: {self.total} POIs guardados")
        logger.info("=" * 70)

async def main():
    scraper = POIScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
