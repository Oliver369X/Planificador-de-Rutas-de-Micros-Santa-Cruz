
import os
import sys

# Agregar directorio raíz al path para importar app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, insert, inspect
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base

# Importar todos los modelos para que Base.metadata los reconozca
# app/__init__.py ya importa todos, así que esto basta
# Si no, importamos uno por uno
try:
    from app.models import (
        line, pattern, pattern_stop, stop, poi, 
        user, favorite, report, trip, route, 
        transfer, payment
    )
except ImportError as e:
    print(f"⚠️ Error importando modelos: {e}")
    # Fallback: importar por nombre si el __init__ no está completo
    from app.models.line import Line
    from app.models.stop import Stop
    from app.models.pattern import Pattern
    from app.models.pattern_stop import PatternStop
    from app.models.poi import PointOfInterest
    from app.models.user import User
    from app.models.favorite import Favorite
    from app.models.report import Report

# URLs de conexión
LOCAL_DB_URL = settings.DATABASE_URL
NEON_DB_URL = "postgresql://neondb_owner:npg_2jTMVC8sPiBh@ep-solitary-moon-a43sbjel-pooler.us-east-1.aws.neon.tech/transporte_db?sslmode=require"

def copy_data():
    print("=== Copiando datos de Local a Neon (V3: Full Models) ===")
    
    local_engine = create_engine(LOCAL_DB_URL)
    neon_engine = create_engine(NEON_DB_URL)
    
    # 1. Crear estructura de tablas en Neon usando los modelos
    print("\n1. Creando tablas en Neon...")
    try:
        Base.metadata.create_all(bind=neon_engine)
        print("   ✅ Estructura creada exitosamente.")
    except Exception as e:
        print(f"   ❌ Error creando tablas: {e}")
        return

    # 2. Definir orden de carga (para respetar FKs)
    # Usamos los nombres de tabla definidos en los modelos (con esquema)
    # Base.metadata.sorted_tables nos da el orden topológico correcto
    tables_to_copy = Base.metadata.sorted_tables
    
    print(f"\nTablas detectadas: {[t.fullname for t in tables_to_copy]}")
    
    # 2. Limpiar tablas en orden inverso para evitar conflictos de FK
    print("\n2. Limpiando tablas destino...")
    with Session(neon_engine) as neon_session:
        for table in reversed(tables_to_copy):
            try:
                print(f"   Limpiando {table.fullname}...")
                neon_session.execute(table.delete())
                neon_session.commit()
            except Exception as e:
                print(f"   ⚠️ Error limpiando {table.fullname}: {e}")
                neon_session.rollback()

    # 3. Copiar datos
    print("\n3. Migrando datos...")
    with Session(local_engine) as local_session, Session(neon_engine) as neon_session:
        for table in tables_to_copy:
            full_table_name = table.fullname # e.g., transporte.lineas
            print(f"\nProcesando tabla: {full_table_name}")
            
            # Verificar si existe en origen
            try:
                # Use inspect to verify table exists in local db
                insp = inspect(local_engine)
                # handle schema
                schema = table.schema
                tname = table.name
                if not insp.has_table(tname, schema=schema):
                    print(f"⚠️ Tabla {full_table_name} no existe en base de datos local (saltando)")
                    continue
            except Exception as e:
                 print(f"⚠️ Error inspeccionando tabla local: {e}")
            
            # Leer datos
            try:
                # Select *
                stmt = select(table)
                results = local_session.execute(stmt).fetchall()
            except Exception as e:
                print(f"⚠️ Error leyendo datos locales: {e}")
                continue
                
            if not results:
                print("   Tabla vacía en origen.")
                continue
            
            print(f"   Copiando {len(results)} registros...")
            
            # Preparar datos
            data_to_insert = []
            keys = table.columns.keys()
            for row in results:
                row_dict = {col: val for col, val in zip(keys, row)}
                data_to_insert.append(row_dict)
            
            # Limpiar tabla destino? (Opcional, arriesgado si hay FKs, mejor confiar en create_all o truncate cascade)
            # neon_session.execute(table.delete())
            
            # Insertar en lotes
            batch_size = 100
            total = len(data_to_insert)
            
            try:
                for i in range(0, total, batch_size):
                    batch = data_to_insert[i:i+batch_size]
                    if not batch: break
                    
                    # Usar Core insert para velocidad
                    neon_session.execute(insert(table), batch)
                    print(f"   ...progresando {min(i+batch_size, total)}/{total}", end='\r')
                
                neon_session.commit()
                print(f"\n   ✅ {total} registros copiados.")
            except Exception as e:
                print(f"\n   ❌ Error insertando datos: {e}")
                neon_session.rollback()
                # Si falla por unique constraint, tal vez ya existen datos.
                # Podríamos intentar limpiar o upsert, pero por ahora reportamos error.

if __name__ == "__main__":
    copy_data()
