"""Verificar datos del scraping"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

print("=" * 70)
print("📊 VERIFICACIÓN DE DATOS SCRAPEADOS")
print("=" * 70)

with engine.connect() as conn:
    # Líneas
    result = conn.execute(text("SELECT COUNT(*) FROM transporte.lineas;"))
    total_lineas = result.fetchone()[0]
    print(f"\n🚍 Total Líneas: {total_lineas}")
    
    # Patterns
    result = conn.execute(text("SELECT COUNT(*) FROM transporte.patterns;"))
    total_patterns = result.fetchone()[0]
    print(f"🛣️  Total Patterns: {total_patterns}")
    
    # Paradas
    result = conn.execute(text("SELECT COUNT(*) FROM transporte.paradas;"))
    total_paradas = result.fetchone()[0]
    print(f"📍 Total Paradas: {total_paradas}")
    
    # Pattern-Stops
    result = conn.execute(text("SELECT COUNT(*) FROM transporte.pattern_stops;"))
    total_ps = result.fetchone()[0]
    print(f"🔗 Total Pattern-Stops: {total_ps}")
    
    # Muestra de líneas
    print("\n" + "=" * 70)
    print("📋 MUESTRA DE LÍNEAS CREADAS:")
    print("=" * 70)
    result = conn.execute(text("""
        SELECT nombre, short_name, color, mode 
        FROM transporte.lineas 
        ORDER BY id_linea 
        LIMIT 10;
    """))
    
    for row in result:
        print(f"  • {row[0]:15} | Short: {row[1]:10} | Color: {row[2]} | Mode: {row[3]}")
    
    # Líneas con más paradas
    print("\n" + "=" * 70)
    print("🏆 TOP 5 LÍNEAS CON MÁS PARADAS:")
    print("=" * 70)
    result = conn.execute(text("""
        SELECT 
            l.nombre,
            COUNT(DISTINCT ps.id_parada) as total_paradas
        FROM transporte.lineas l
        JOIN transporte.patterns p ON l.id_linea = p.id_linea
        JOIN transporte.pattern_stops ps ON p.id = ps.pattern_id
        GROUP BY l.id_linea, l.nombre
        ORDER BY total_paradas DESC
        LIMIT 5;
    """))
    
    for row in result:
        print(f"  • Línea {row[0]:15} : {row[1]:3} paradas")
    
    # Patterns por sentido
    print("\n" + "=" * 70)
    print("📊 PATTERNS POR SENTIDO:")
    print("=" * 70)
    result = conn.execute(text("""
        SELECT sentido, COUNT(*) as total
        FROM transporte.patterns
        GROUP BY sentido;
    """))
    
    for row in result:
        print(f"  • {row[0].capitalize():10} : {row[1]} patterns")

print("\n" + "="  * 70)
print("✅ VERIFICACIÓN COMPLETADA")
print("=" * 70)
