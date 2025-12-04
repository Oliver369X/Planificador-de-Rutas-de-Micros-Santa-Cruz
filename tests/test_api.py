"""Test manual de la API de Guía Urbana"""
import asyncio
import httpx
import json

async def test_api():
    print("🧪 Probando API Guía Urbana Municipal...\n")
    
    base_url = "https://guiaurbana.gmsantacruz.gob.bo/guiaurbana/public/api"
    
    # Probar algunas rutas conocidas
    test_routes = [1, 2, 15, 27, 90]
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        for route_id in test_routes:
            url = f"{base_url}/rutaMicrobuses/{route_id}"
            print(f"📥 Probando ruta {route_id}...")
            print(f"   URL: {url}")
            
            try:
                response = await client.get(url)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Tipo: {data.get('type', 'N/A')}")
                    features = data.get('features', [])
                    print(f"   Features: {len(features)}")
                    
                    if features:
                        first = features[0]
                        props = first.get('properties', {})
                        print(f"   Nombre: {props.get('nombre', 'N/A')}")
                        print(f"   Sentido: {props.get('sentido', 'N/A')}")
                        print(f"   ✅ Datos válidos\n")
                    else:
                        print(f"   ⚠️  Sin features\n")
                else:
                    print(f"   ❌ Error HTTP\n")
                    
            except Exception as e:
                print(f"   ❌ Excepción: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_api())
