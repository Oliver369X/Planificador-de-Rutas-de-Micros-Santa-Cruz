from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Coordenadas aproximadas del usuario (del laboratorio en la imagen)
user_lat = -17.777
user_lon = -63.182

# Buscar paradas cercanas
print(f"=== Paradas cercanas a ({user_lat}, {user_lon}) ===")
stops = db.execute(text("""
    SELECT id_parada, nombre_parada, latitud, longitud,
           ST_Distance(
               geom::geography, 
               ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
           ) as distance
    FROM transporte.paradas
    WHERE ST_DWithin(
        geom::geography,
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
        2000
    )
    ORDER BY distance ASC
    LIMIT 20
"""), {"lat": user_lat, "lon": user_lon}).fetchall()

print(f"Paradas encontradas: {len(stops)}")
for s in stops:
    print(f"  {s.nombre_parada}: {s.distance:.0f}m")

# Ahora ver qué líneas pasan por esas paradas
print("\n=== Líneas que pasan por las paradas cercanas ===")
stop_ids = [s.id_parada for s in stops]
if stop_ids:
    lines = db.execute(text("""
        SELECT DISTINCT l.short_name, l.nombre
        FROM transporte.pattern_stops ps
        JOIN transporte.patterns p ON ps.pattern_id = p.id
        JOIN transporte.lineas l ON p.id_linea = l.id_linea
        WHERE ps.id_parada = ANY(:stop_ids)
        ORDER BY l.short_name
    """), {"stop_ids": stop_ids}).fetchall()
    
    print(f"Líneas: {len(lines)}")
    for l in lines:
        print(f"  Línea {l.short_name}: {l.nombre}")
