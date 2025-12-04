from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM pg_available_extensions WHERE name = 'postgis'"))
        row = result.fetchone()
        if row:
            print(f"PostGIS is available: {row}")
        else:
            print("PostGIS is NOT available in pg_available_extensions.")
            
        # Check if already installed
        result_installed = connection.execute(text("SELECT * FROM pg_extension WHERE extname = 'postgis'"))
        row_installed = result_installed.fetchone()
        if row_installed:
            print(f"PostGIS is already installed: {row_installed}")
        else:
            print("PostGIS is NOT installed in the current database.")
            
except Exception as e:
    print(f"Error checking PostGIS: {e}")
