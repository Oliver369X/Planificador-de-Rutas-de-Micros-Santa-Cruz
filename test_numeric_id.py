import requests

# Probar con un ID numérico (como lo envía trufi-core)
print("Probando pattern(id: '42') - ID numérico...")

detail_query = '''
{
    pattern(id: "42") {
        id
        geometry { lat lon }
        stops { name lat lon }
    }
}
'''
r = requests.post('http://localhost:8000/graphql', json={'query': detail_query})
detail = r.json()

if 'data' in detail and detail['data']['pattern']:
    p = detail['data']['pattern']
    print(f"  Pattern ID devuelto: {p['id']}")
    print(f"  Geometry points: {len(p.get('geometry', []))}")
    print(f"  Stops: {len(p.get('stops', []))}")
    if p.get('stops'):
        print(f"  Primera parada: {p['stops'][0]}")
    if p.get('geometry'):
        print(f"  Primer punto: {p['geometry'][0]}")
else:
    print(f"  Error o sin datos: {detail}")

# Probar con ID "3" también
print("\nProbando pattern(id: '3') - Otro ID numérico...")
detail_query2 = '''
{
    pattern(id: "3") {
        id
        geometry { lat lon }
        stops { name lat lon }
    }
}
'''
r2 = requests.post('http://localhost:8000/graphql', json={'query': detail_query2})
detail2 = r2.json()

if 'data' in detail2 and detail2['data']['pattern']:
    p2 = detail2['data']['pattern']
    print(f"  Pattern ID devuelto: {p2['id']}")
    print(f"  Geometry points: {len(p2.get('geometry', []))}")
    print(f"  Stops: {len(p2.get('stops', []))}")
else:
    print(f"  Error o sin datos: {detail2}")
