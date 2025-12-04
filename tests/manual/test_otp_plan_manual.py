import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Agregar root al path (3 niveles arriba desde tests/manual)
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from app.main import app

load_dotenv()

def test_otp_plan_manual():
    print("🔧 Iniciando prueba manual de endpoint /plan...")
    
    # 1. Obtener coordenadas reales de la BD
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL no definida en .env")
        return

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Buscar una ruta con al menos 10 paradas y obtener la 1ra y la 10ma
            query = text("""
                SELECT 
                    l.nombre as nombre_linea, 
                    p1.latitud as lat1, p1.longitud as lon1, 
                    p2.latitud as lat2, p2.longitud as lon2 
                FROM transporte.patterns p 
                JOIN transporte.pattern_stops ps1 ON p.id = ps1.pattern_id 
                JOIN transporte.pattern_stops ps2 ON p.id = ps2.pattern_id 
                JOIN transporte.paradas p1 ON ps1.id_parada = p1.id_parada 
                JOIN transporte.paradas p2 ON ps2.id_parada = p2.id_parada 
                JOIN transporte.lineas l ON p.id_linea = l.id_linea 
                WHERE ps1.sequence = 1 AND ps2.sequence = 10 
                LIMIT 1
            """)
            result = conn.execute(query).fetchone()
            
            if not result:
                print("⚠️ No se encontraron rutas con suficientes paradas para la prueba.")
                # Fallback coordinates (Plaza 24 de Septiembre -> Parque Urbano)
                from_place = "-17.7833,-63.1821"
                to_place = "-17.7950,-63.1750"
                print(f"   Usando coordenadas fallback: {from_place} -> {to_place}")
            else:
                nombre_linea, lat1, lon1, lat2, lon2 = result
                from_place = f"{lat1},{lon1}"
                to_place = f"{lat2},{lon2}"
                print(f"✅ Ruta encontrada para prueba: Línea {nombre_linea}")
                print(f"   Origen: {from_place}")
                print(f"   Destino: {to_place}")

    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return

    # 2. Probar endpoint
    client = TestClient(app)
    
    print("\n📡 Enviando request a /api/v1/plan...")
    response = client.get(
        "/api/v1/plan",
        params={
            "fromPlace": from_place,
            "toPlace": to_place,
            "date": "12-03-2025",
            "time": "12:00:00",
            "numItineraries": 3
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Respuesta exitosa (200 OK)")
        
        plan = data.get("plan", {})
        itineraries = plan.get("itineraries", [])
        
        print(f"📊 Itinerarios encontrados: {len(itineraries)}")
        
        if itineraries:
            for i, it in enumerate(itineraries):
                print(f"\n   🚌 Itinerario {i+1}:")
                print(f"      Duración: {it['duration']} seg")
                print(f"      Caminata: {it['walkDistance']} m")
                print(f"      Transbordos: {it['transfers']}")
                print("      Pasos:")
                for leg in it['legs']:
                    mode = leg['mode']
                    route = leg.get('route', '')
                    print(f"        - {mode} {route} ({leg['duration']}s)")
        else:
            print("⚠️  No se encontraron itinerarios (posiblemente muy lejos o sin conexión directa)")
            
    else:
        print(f"❌ Error en request: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_otp_plan_manual()
