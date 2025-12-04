import requests

# Probar que la ruta 14 ahora devuelve los datos correctos
print("Testing pattern(id: '14') - Should now return correct route 14 data...")

r = requests.post('http://localhost:8000/graphql', json={
    'query': '{ pattern(id: "14") { id geometry { lat lon } stops { name lat lon } } }'
})

data = r.json()

if 'data' in data and data['data']['pattern']:
    p = data['data']['pattern']
    print(f"Pattern ID: {p['id']}")
    print(f"Geometry points: {len(p.get('geometry', []))}")
    print(f"Stops: {len(p.get('stops', []))}")
    
    if p.get('geometry') and len(p.get('geometry', [])) > 1:
        # Mostrar primeros puntos para verificar
        print(f"\nFirst 3 geometry points:")
        for i, pt in enumerate(p['geometry'][:3]):
            print(f"  {i}: lat={pt['lat']}, lon={pt['lon']}")
        
        # La ruta 14 según guiaurbana empieza cerca de: -63.122769, -17.728882
        # Verificar si coincide
        first_lon = p['geometry'][0]['lon']
        first_lat = p['geometry'][0]['lat']
        
        # Comparar con guiaurbana (primer punto: -63.122769457, -17.728882262)
        expected_lon = -63.122769457
        expected_lat = -17.728882262
        
        if abs(first_lon - expected_lon) < 0.01 and abs(first_lat - expected_lat) < 0.01:
            print(f"\n✅ Geometry matches guiaurbana route 14!")
        else:
            print(f"\n⚠️  Geometry doesn't match. First point: {first_lat}, {first_lon}")
            print(f"    Expected near: {expected_lat}, {expected_lon}")
    else:
        print("⚠️  No geometry or only 1 point (fallback)")
else:
    print(f"Error: {data}")
