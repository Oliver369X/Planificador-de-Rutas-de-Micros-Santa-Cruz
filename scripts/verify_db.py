"""Verificar estado de la base de datos"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:071104@localhost:5432/transporte_db")

engine = create_engine(DATABASE_URL)

print("🔍 Verificando estado de la base de datos...\n")

with engine.connect() as conn:
    # Verificar schema transporte
    result = conn.execute(text("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name = 'transporte';
    """))
    
    if result.fetchone():
        print("✅ Schema 'transporte' existe\n")
    else:
        print("❌ Schema 'transporte' NO existe - creándolo...")
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS transporte;"))
        conn.commit()
        print("✅ Schema 'transporte' creado\n")
    
    # Verificar tablas
    result = conn.execute(text("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'transporte'
        ORDER BY tablename;
    """))
    
    tables = [row[0] for row in result]
    
    if tables:
        print(f"📊 Tablas en schema 'transporte' ({len(tables)}):")
        for table in tables:
            print(f"   - {table}")
    else:
        print("⚠️  No hay tablas en schema 'transporte'")
        print("   Necesitas ejecutar las migraciones base primero")
    
    # Verificar PostGIS
    print("\n🗺️  Verificando PostGIS...")
    try:
        result = conn.execute(text("SELECT PostGIS_Version();"))
        version = result.fetchone()[0]
        print(f"✅ PostGIS instalado: {version}")
    except:
        print("❌ PostGIS NO instalado/habilitado")
