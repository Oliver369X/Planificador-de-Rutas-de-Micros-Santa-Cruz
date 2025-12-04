"""Test para ver formato exacto de la respuesta de API"""
import asyncio
import httpx
import json

async def test_format():
    client = httpx.AsyncClient(timeout=20.0)
    
    url = "https://guiaurbana.gmsantacruz.gob.bo/guiaurbana/public/api/rutaMicrobuses/1"
    
    print(f"📥 Fetching: {url}\n")
    
    response = await client.get(url)
    data = response.json()
    
    print(f"Tipo de respuesta: {type(data)}")
    print(f"\nPrimeros 500 caracteres:")
    print(json.dumps(data, indent=2)[:500])
    
    await client.aclose()

asyncio.run(test_format())
