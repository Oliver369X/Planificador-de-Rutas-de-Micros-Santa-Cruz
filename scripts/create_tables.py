"""Crear todas las tablas desde los modelos SQLAlchemy"""
import sys
import os

# Agregar path del backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import Line, Stop, Route, Transfer, Trip, Payment, User, Pattern, PatternStop

print("🔧 Creando todas las tablas desde modelos SQLAlchemy...\n")

try:
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    print("✅ Tablas creadas exitosamente!")
    
    # Verificar
    from sqlalchemy import inspect
    inspector = inspect(engine)
    schemas = ['transporte', 'public']
    
    for schema in schemas:
        tables = inspector.get_table_names(schema=schema)
        if tables:
            print(f"\n📊 Tablas en schema '{schema}':")
            for table in tables:
                print(f"   ✓ {table}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    raise
