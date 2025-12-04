import requests
import json

# Centro a Centro
from_lat, from_lon = -17.7833, -63.1821
to_lat, to_lon = -17.79, -63.17

url = f"http://localhost:8000/api/v1/plan?fromPlace={from_lat},{from_lon}&toPlace={to_lat},{to_lon}"

r = requests.get(url)
data = r.json()

print(f"Itinerarios: {len(data['plan']['itineraries'])}")

for i, it in enumerate(data['plan']['itineraries']):
    duration_min = it['duration'] // 60
    transfers = it['transfers']
    buses = [leg.get('routeShortName', '') for leg in it['legs'] if leg['mode'] == 'BUS']
    print(f"  Opcion {i+1}: {duration_min} min, {transfers} transbordo(s), Buses: {buses}")
