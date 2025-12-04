# Solución al Error de PostGIS

## ❌ Error Actual
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedObject) type "geometry" does not exist
LINE 7:  geom geometry(POINT,4326),
```

## ✅ Solución

### Opción 1: Instalar PostGIS en PostgreSQL (RECOMENDADO)

1. **Ejecuta este comando en tu terminal de PostgreSQL:**

```bash
psql -U postgres -d transporte_db
```

2. **Dentro de psql, ejecuta:**

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
SELECT PostGIS_Version();
```

3. **Sal de psql:**

```
\q
```

### Opción 2: Usar pgAdmin

1. Abre pgAdmin
2. Conecta a tu servidor PostgreSQL
3. Navega a: `Servers → PostgreSQL → Databases → transporte_db`
4. Click derecho en "Extensions" → CREATE → Extension
5. Busca "postgis" y haz click en Save

### Opción 3: Comando directo desde PowerShell

```powershell
# Desde el directorio del proyecto
$env:PGPASSWORD="071104"
psql -U postgres -d transporte_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

## 🔍 Verificar la Instalación

Después de instalar PostGIS, ejecuta:

```bash
python check_postgis.py
```

## 🚀 Reiniciar el Servidor

Una vez instalado PostGIS:

```bash
cd backend
uvicorn app.main:app --reload
```

## 📝 Nota Importante

Si **no puedes instalar PostGIS** (por ejemplo, en hosting compartido), 
necesitaremos modificar los modelos para NO usar tipos geométricos.
