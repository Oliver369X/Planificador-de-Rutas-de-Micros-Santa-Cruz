-- Ejecutar como superusuario de PostgreSQL
-- psql -U postgres -d tu_base_de_datos -f install_postgis.sql

-- Crear la extensión PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verificar que se instaló correctamente
SELECT PostGIS_Version();
