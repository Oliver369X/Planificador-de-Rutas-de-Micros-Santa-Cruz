import requests

# Probar el endpoint patterns para ver qué IDs devuelve
query = '''
{
    patterns {
        id
        name
        code
        route {
            shortName
            longName
        }
    }
}
'''

r = requests.post('http://localhost:8000/graphql', json={'query': query})
data = r.json()

if 'data' in data and 'patterns' in data['data']:
    patterns = data['data']['patterns'][:5]
    print(f"Primeros 5 patterns de GraphQL:")
    for p in patterns:
        print(f"  ID: {p['id']}, Name: {p['name']}, Code: {p['code']}")
else:
    print(f"Error: {data}")

# Ahora probar pattern detail con uno de esos IDs
if patterns:
    test_id = patterns[0]['id']
    print(f"\nProbando pattern(id: '{test_id}')...")
    
    detail_query = f'''
    {{
        pattern(id: "{test_id}") {{
            id
            geometry {{ lat lon }}
            stops {{ name lat lon }}
        }}
    }}
    '''
    r2 = requests.post('http://localhost:8000/graphql', json={'query': detail_query})
    detail = r2.json()
    
    if 'data' in detail and detail['data']['pattern']:
        p = detail['data']['pattern']
        print(f"  Geometry points: {len(p.get('geometry', []))}")
        print(f"  Stops: {len(p.get('stops', []))}")
        if p.get('stops'):
            print(f"  Primera parada: {p['stops'][0]}")
    else:
        print(f"  Error: {detail}")
