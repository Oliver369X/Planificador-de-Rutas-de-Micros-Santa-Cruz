import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Agregar root al path (3 niveles arriba desde tests/manual)
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine, text

load_dotenv()

def test_geocoding_manual():
    print("🔧 Iniciando prueba manual de Geocodificación...")
    
    client = TestClient(app)
    
    # 1. Búsqueda (Search)
    print("\n🔍 Probando Búsqueda (/api/v1/geocode/search)...")
    term = "Plaza"
    response = client.get(f"/api/v1/geocode/search?q={term}&limit=5")
    
    if response.status_code == 200:
        data = response.json()
        features = data.get("features", [])
        print(f"✅ Búsqueda exitosa para '{term}': {len(features)} resultados")
        for f in features:
            props = f["properties"]
            print(f"   - {props['name']} ({props['osm_value']})")
    else:
        print(f"❌ Error en búsqueda: {response.status_code}")
        print(response.text)

    # 2. Reverse Geocoding
    print("\n📍 Probando Reverse Geocoding (/api/v1/geocode/reverse)...")
    # Usar coordenadas de la Plaza 24 de Septiembre aprox
    lat = -17.7833
    lon = -63.1821
    
    response = client.get(f"/api/v1/geocode/reverse?lat={lat}&lon={lon}")
    
    if response.status_code == 200:
        data = response.json()
        features = data.get("features", [])
        if features:
            props = features[0]["properties"]
            print(f"✅ Reverse exitoso para {lat},{lon}")
            print(f"   Lugar más cercano: {props['name']}")
            print(f"   Distancia: {props.get('distance', 'N/A')} metros")
        else:
            print("⚠️  No se encontró nada cerca")
    else:
        print(f"❌ Error en reverse: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_geocoding_manual()
