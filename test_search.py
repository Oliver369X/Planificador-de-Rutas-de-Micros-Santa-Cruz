import requests

# Probar varios términos de búsqueda
terminos = ['hospital', 'mercado', 'escuela', 'universidad', 'terminal']

for t in terminos:
    r = requests.get(f'http://localhost:8000/api?q={t}')
    d = r.json()
    print(f'\n"{t}": {len(d["features"])} resultados')
    for f in d['features'][:3]:
        print(f"  - {f['properties']['name'][:40]}")
