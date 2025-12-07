from app.database import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
r = db.execute(text('SELECT objectid, nombre, tipo, latitud, longitud FROM transporte.points_of_interest LIMIT 100')).fetchall()

features = []
for p in r:
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [float(p[4]), float(p[3])]
        },
        'properties': {
            'name': p[1],
            'type': p[2],
            'id': str(p[0])
        }
    })

result = {'type': 'FeatureCollection', 'features': features}
output_path = '../trufi-core/apps/example/assets/data/search.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'Exportados {len(features)} POIs a {output_path}')
