import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Agregar root al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app

load_dotenv()

def test_trufi_compatibility():
    print("🔧 Probando Compatibilidad con trufi-core...")
    
    client = TestClient(app)
    
    # 1. Test Photon Search (/api)
    print("\n🔍 Probando Photon Search (/api?q=...)...")
    resp = client.get("/api?q=Plaza")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Photon Search OK. Features: {len(data['features'])}")
        if data['features']:
            print(f"   Ejemplo: {data['features'][0]['properties']['name']}")
    else:
        print(f"❌ Error Photon Search: {resp.status_code}")
        print(resp.text)

    # 2. Test Photon Reverse (/reverse)
    print("\n📍 Probando Photon Reverse (/reverse?lat=...&lon=...)...")
    resp = client.get("/reverse?lat=-17.7833&lon=-63.1821")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Photon Reverse OK. Features: {len(data['features'])}")
        if data['features']:
            print(f"   Lugar: {data['features'][0]['properties']['name']}")
    else:
        print(f"❌ Error Photon Reverse: {resp.status_code}")
        print(resp.text)

    # 3. Test GraphQL patterns
    print("\n🚌 Probando GraphQL /graphql (patterns)...")
    query = """
    {
      patterns {
        id
        name
        route {
          longName
          shortName
          color
        }
      }
    }
    """
    resp = client.post("/graphql", json={"query": query})
    if resp.status_code == 200:
        data = resp.json()
        if "errors" not in data:
            patterns = data["data"]["patterns"]
            print(f"✅ GraphQL Patterns OK. Total: {len(patterns)}")
            if patterns:
                print(f"   Ejemplo: {patterns[0]['name']} ({patterns[0]['route']['shortName']})")
        else:
            print(f"❌ Error GraphQL: {data['errors']}")
    else:
        print(f"❌ Error GraphQL: {resp.status_code}")
        print(resp.text)

    # 4. Test GraphQL pattern detail
    print("\n🗺️ Probando GraphQL pattern(id) con geometría...")
    # Primero obtenemos un ID válido
    if resp.status_code == 200 and "errors" not in resp.json():
        first_pattern_id = resp.json()["data"]["patterns"][0]["id"]
        detail_query = f"""
        {{
          pattern(id: "{first_pattern_id}") {{
            geometry {{ lat lon }}
            stops {{ name lat lon }}
          }}
        }}
        """
        resp = client.post("/graphql", json={"query": detail_query})
        if resp.status_code == 200:
            data = resp.json()
            if "errors" not in data:
                pattern = data["data"]["pattern"]
                geom_count = len(pattern["geometry"]) if pattern["geometry"] else 0
                stops_count = len(pattern["stops"]) if pattern["stops"] else 0
                print(f"✅ Pattern Detail OK. Puntos: {geom_count}, Paradas: {stops_count}")
            else:
                print(f"❌ Error GraphQL Detail: {data['errors']}")

if __name__ == "__main__":
    test_trufi_compatibility()
