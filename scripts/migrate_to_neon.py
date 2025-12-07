"""
Script para migrar datos de PostgreSQL local a Neon
Ejecutar: python scripts/migrate_to_neon.py
"""
import os
import subprocess
import sys

# URLs de conexión
LOCAL_DB = "postgresql://user:password@localhost:5432/transporte_db"
NEON_DB = os.getenv("NEON_DATABASE_URL", 
    "postgresql://neondb_owner:npg_2jTMVC8sPiBh@ep-solitary-moon-a43sbjel-pooler.us-east-1.aws.neon.tech/transporte_db?sslmode=require"
)

def migrate():
    print("=== Migración a Neon PostgreSQL ===\n")
    
    # 1. Exportar datos locales
    print("1. Exportando datos locales...")
    dump_file = "backup_local.sql"
    
    # Exportar estructura y datos del schema transporte
    dump_cmd = f'pg_dump --schema=transporte --no-owner --no-acl -h localhost -U user transporte_db > {dump_file}'
    print(f"   Comando: {dump_cmd}")
    print("   [Ejecutar manualmente si pg_dump no está en PATH]\n")
    
    # 2. Crear extensión PostGIS en Neon
    print("2. Crear PostGIS en Neon (ejecutar en psql):")
    print("   CREATE EXTENSION IF NOT EXISTS postgis;")
    print("   CREATE SCHEMA IF NOT EXISTS transporte;\n")
    
    # 3. Importar a Neon
    print("3. Importar datos a Neon:")
    print(f"   psql '{NEON_DB}' < {dump_file}\n")
    
    # Instrucciones manuales
    print("=== Pasos Manuales ===")
    print("""
1. Conectarse a Neon:
   psql 'postgresql://neondb_owner:npg_2jTMVC8sPiBh@ep-solitary-moon-a43sbjel-pooler.us-east-1.aws.neon.tech/transporte_db?sslmode=require'

2. Crear PostGIS y schema:
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE SCHEMA IF NOT EXISTS transporte;

3. Exportar datos locales:
   pg_dump --schema=transporte --no-owner -h localhost -U postgres transporte_db > backup.sql

4. Importar a Neon:
   psql 'postgresql://neondb_owner:...@...neon.tech/transporte_db?sslmode=require' < backup.sql

5. Verificar:
   SELECT COUNT(*) FROM transporte.lineas;
   SELECT COUNT(*) FROM transporte.paradas;
   SELECT COUNT(*) FROM transporte.patterns;
""")

if __name__ == "__main__":
    migrate()
