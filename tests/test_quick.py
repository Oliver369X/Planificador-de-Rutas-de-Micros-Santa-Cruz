"""Test rápido de scraping"""
import asyncio
import httpx

async def test():
    client = httpx.AsyncClient(timeout=20.0)
    
    # Probar ruta 1
    url = "https://guiaurbana.gmsantacruz.gob.bo/guiaurbana/public/api/rutaMicrobuses/1"
    response = await client.get(url)
    data = response.json()
    
    print("Tipo de respuesta:", type(data))
    print("Es lista?:", isinstance(data, list))
    
    if isinstance(data, list) and len(data) > 0:
        first_item = data[0]
        print("Primer item tipo:", type(first_item))
        print("Es dict?:", isinstance(first_item, dict))
        print("Tiene 'features'?:", "features" in first_item if isinstance(first_item, dict) else False)
        
        if isinstance(first_item, dict):
            print("Keys:", list(first_item.keys()))
            if "features" in first_item:
                print("Num features:", len(first_item["features"]))
                print("Features es None?:", first_item["features"] is None)
    
    await client.aclose()

asyncio.run(test())
