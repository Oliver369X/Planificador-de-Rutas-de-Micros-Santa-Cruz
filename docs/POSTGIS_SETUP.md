# Verificación e Instalación de PostGIS

## ✅ ¿Necesitas PostGIS?

**SÍ**, porque usamos:
- Geometrías: `POINT`, `LINESTRING` 
- Funciones: `ST_DWithin`, `ST_Distance`, `ST_MakePoint`
- Índices espaciales: `GIST`

---

## 1. Verificar si PostGIS está instalado

```bash
# Opción A: Verificar en la base de datos
psql -U postgres -d transporte_db -c "SELECT PostGIS_Version();"

# Si funciona, verás algo como:
# 3.3 USE_GEOS=1 USE_PROJ=1 USE_STATS=1

# Si da error: "function postgis_version() does not exist"
# → Necesitas instalar PostGIS
```

```sql
-- Opción B: Verificar extensiones instaladas
SELECT * FROM pg_available_extensions WHERE name = 'postgis';

-- Verificar extensiones habilitadas en tu BD
SELECT * FROM pg_extension WHERE extname = 'postgis';
```

---

## 2. Instalar PostGIS (si no lo tienes)

### Windows

```powershell
# Si instalaste PostgreSQL con StackBuilder:
# 1. Abre StackBuilder
# 2. Selecciona tu instalación de PostgreSQL
# 3. En "Spatial Extensions" → selecciona PostGIS
# 4. Instalar

# Si usaste EDB installer:
# PostGIS suele venir incluido, solo necesitas habilitarlo
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgis postgresql-14-postgis-3
# Cambia "14" por tu versión de PostgreSQL
```

### macOS

```bash
# Con Homebrew
brew install postgis
```

---

## 3. Habilitar PostGIS en tu Base de Datos

```bash
# Conectar a tu base de datos
psql -U postgres -d transporte_db
```

```sql
-- Dentro de psql:

-- Habilitar extensión PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verificar versión
SELECT PostGIS_Version();

-- Verificar que se crearon las funciones espaciales
SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'st_%';
-- Deberías ver 500+ funciones

-- Salir
\q
```

---

## 4. Verificación Completa

```sql
-- Probar funciones PostGIS
SELECT ST_AsText(ST_MakePoint(-63.1821, -17.7834));
-- Debería devolver: "POINT(-63.1821 -17.7834)"

-- Probar distancia
SELECT ST_Distance(
    ST_MakePoint(-63.1821, -17.7834)::geography,
    ST_MakePoint(-63.1823, -17.7835)::geography
);
-- Debería devolver un número (metros)

-- Verificar que puedes crear geometrías
CREATE TABLE test_geom (
    id SERIAL PRIMARY KEY,
    geom geometry(POINT, 4326)
);

INSERT INTO test_geom (geom) 
VALUES (ST_SetSRID(ST_MakePoint(-63.1821, -17.7834), 4326));

SELECT ST_AsText(geom) FROM test_geom;

DROP TABLE test_geom;
```

---

## 5. Si ya tenías PostGIS pero no estaba habilitado

Si ya tenías PostgreSQL con PostGIS instalado pero no lo habías habilitado en `transporte_db`:

```sql
-- Conectar
psql -U postgres -d transporte_db

-- Habilitar
CREATE EXTENSION postgis;

-- Ahora ejecuta la migración
\i migrations/001_trufi_core_schema.sql

-- Verificar tablas
\dt transporte.*;
```

---

## 6. Errores Comunes y Soluciones

### Error: "could not load library postgis-3.dll"

**Solución Windows:**
```powershell
# Reinstalar PostGIS con StackBuilder
# O descargar desde:
# https://postgis.net/windows_downloads/
```

### Error: "extension postgis not found"

**Solución:**
```bash
# Verificar que postgis está en el directorio de extensiones
ls /usr/share/postgresql/14/extension/postgis*

# Si no está, instalar:
sudo apt install postgresql-14-postgis-3
```

### Error: "type geometry does not exist"

**Causa:** PostGIS no habilitado en la base de datos

**Solución:**
```sql
CREATE EXTENSION postgis;
```

---

## ✅ Checklist Final

- [ ] PostGIS instalado en el sistema
- [ ] Extension habilitada: `CREATE EXTENSION postgis;`
- [ ] Funciones ST_* disponibles
- [ ] Migración ejecutada sin errores
- [ ] Scraper puede crear geometrías

---

## 🚀 Después de Habilitar PostGIS

```bash
# 1. Habilitar extensión
psql -U postgres -d transporte_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 2. Ejecutar migración
psql -U postgres -d transporte_db -f migrations/001_trufi_core_schema.sql

# 3. Verificar tablas creadas
psql -U postgres -d transporte_db -c "\d transporte.patterns"

# Deberías ver la columna:
# geometry | geometry(LineString,4326) |

# 4. Ejecutar scraper
python scraper_guia_urbana.py
```
