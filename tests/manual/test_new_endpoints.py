import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Agregar root al path (2 niveles arriba desde tests/manual)
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app

load_dotenv()

def test_new_endpoints():
    print("🔧 Probando Nuevos Endpoints...")
    
    client = TestClient(app)
    
    # 1. Test Line Route
    print("\n🚌 Probando GET /api/v1/lines/{id}/route...")
    # Asumimos que existe la línea con ID 1 (o buscamos una)
    # Primero listamos líneas para obtener un ID válido
    lines_resp = client.get("/api/v1/lines/")
    if lines_resp.status_code == 200 and len(lines_resp.json()) > 0:
        line_id = lines_resp.json()[0]["id_linea"]
        print(f"   Usando Línea ID: {line_id}")
        
        resp = client.get(f"/api/v1/lines/{line_id}/route")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Route OK. Features: {len(data['features'])}")
        else:
            print(f"❌ Error Route: {resp.status_code}")
    else:
        print("⚠️ No se pudieron listar líneas para probar ruta")

    # 2. Test POI Categories
    print("\n🏷️  Probando GET /api/v1/pois/categories...")
    resp = client.get("/api/v1/pois/categories")
    if resp.status_code == 200:
        cats = resp.json()
        print(f"✅ Categorías: {cats}")
    else:
        print(f"❌ Error Categories: {resp.status_code}")

    # 3. Test POIs Filter
    print("\n📍 Probando GET /api/v1/pois?category=educacion...")
    resp = client.get("/api/v1/pois?category=educacion&limit=5")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ POIs Educacion: {len(data['features'])}")
    else:
        print(f"❌ Error POIs: {resp.status_code}")

if __name__ == "__main__":
    test_new_endpoints()
