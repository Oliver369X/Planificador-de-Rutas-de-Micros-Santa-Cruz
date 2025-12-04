from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Ver puntos de geometría del pattern 11 (que es la ruta 14)
print("=== Geometría del pattern:11:ida ===")
try:
    r = db.execute(text("""
        SELECT ST_NPoints(geometry) as num_points
        FROM transporte.patterns
        WHERE id = 'pattern:11:ida'
    """)).fetchone()
    if r:
        print(f"  Número de puntos: {r[0]}")
    
    # Obtener primeros 10 puntos
    r = db.execute(text("""
        SELECT 
            (dp).path[1] as idx,
            ST_Y((dp).geom) as lat,
            ST_X((dp).geom) as lon
        FROM (
            SELECT ST_DumpPoints(geometry) as dp
            FROM transporte.patterns
            WHERE id = 'pattern:11:ida'
        ) sub
        ORDER BY idx
        LIMIT 10
    """)).fetchall()
    print("\n  Primeros puntos:")
    for row in r:
        print(f"    {row[0]}: lat={row[1]:.6f}, lon={row[2]:.6f}")
        
except Exception as e:
    print(f"  Error: {e}")

db.close()
