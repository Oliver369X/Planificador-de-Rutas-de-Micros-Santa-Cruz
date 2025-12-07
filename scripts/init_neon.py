
import os
import psycopg2
from urllib.parse import urlparse

# URL de Neon proporcionada por el usuario
NEON_DB_URL = "postgresql://neondb_owner:npg_2jTMVC8sPiBh@ep-solitary-moon-a43sbjel-pooler.us-east-1.aws.neon.tech/transporte_db?sslmode=require"

def init_db():
    print("Conectando a Neon DB...")
    
    try:
        conn = psycopg2.connect(NEON_DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Creando extensión PostGIS...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        print("Creando esquema 'transporte'...")
        cur.execute("CREATE SCHEMA IF NOT EXISTS transporte;")
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Inicialización completada exitosamente.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    init_db()
