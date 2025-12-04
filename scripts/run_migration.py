"""
Script para ejecutar la migración de base de datos desde Python
"""
from sqlalchemy import create_engine, text
import os

# Leer DATABASE_URL desde .env
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:071104@localhost:5432/transporte_db")

print(f"🔧 Conectando a: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

# Leer archivo SQL
with open('migrations/001_trufi_core_schema.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

print("📝 Ejecutando migración...")

try:
    with engine.connect() as conn:
        # Primero habilitar PostGIS
        print("  → Habilitando PostGIS...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
        
        # Ejecutar el archivo de migración
        print("  → Ejecutando schema...")
        conn.execute(text(sql_content))
        conn.commit()
        
    print("✅ Migración completada exitosamente!")
    
    # Verificar tablas
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'transporte'
            ORDER BY tablename;
        """))
        
        print("\n📊 Tablas en schema 'transporte':")
        for row in result:
            print(f"   - {row[0]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    raise
