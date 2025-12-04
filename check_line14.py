from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Ver si hay línea 14 y qué nombre tiene
print("=== Buscando línea 14 ===")
r = db.execute(text("SELECT id_linea, nombre FROM transporte.lineas WHERE id_linea = 14"))
for row in r.fetchall():
    print(f"id_linea={row[0]}, nombre={row[1]}")

# Ver líneas que tienen "14" en el nombre
print("\n=== Líneas con '14' en el nombre ===")
r = db.execute(text("SELECT id_linea, nombre FROM transporte.lineas WHERE nombre LIKE '%14%' LIMIT 10"))
for row in r.fetchall():
    print(f"id_linea={row[0]}, nombre={row[1]}")

# Ver patterns de la línea 14
print("\n=== Patterns de la línea 14 ===")
r = db.execute(text("SELECT id, name, id_linea FROM transporte.patterns WHERE id_linea = 14"))
for row in r.fetchall():
    print(f"id={row[0]}, name={row[1]}, id_linea={row[2]}")

# Ver cuántas paradas tiene el pattern de línea 14
print("\n=== Paradas del pattern de línea 14 ===")
r = db.execute(text("""
    SELECT ps.pattern_id, COUNT(*) as stops 
    FROM transporte.pattern_stops ps 
    JOIN transporte.patterns p ON ps.pattern_id = p.id 
    WHERE p.id_linea = 14 
    GROUP BY ps.pattern_id
"""))
for row in r.fetchall():
    print(f"pattern_id={row[0]}, stops={row[1]}")

db.close()
