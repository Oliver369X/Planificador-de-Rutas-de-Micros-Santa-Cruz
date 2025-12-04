# 🚀 QUICK START - Fase 0 y 1: Scraping y Modelos

## ✅ Pasos para Ejecutar

### 1. Ejecutar Migración de Base de Datos

```bash
cd backend

# Opción A: Con psql directamente
psql -U postgres -d transporte_db -f migrations/001_trufi_core_schema.sql

# Opción B: Desde Python
python -c "from sqlalchemy import create_engine, text; \
engine = create_engine('postgresql://postgres:071104@localhost:5432/transporte_db'); \
with engine.connect() as conn: \
    with open('migrations/001_trufi_core_schema.sql', 'r') as f: \
        conn.execute(text(f.read())); conn.commit()"
```

**Verificar:**
```bash
psql -U postgres -d transporte_db -c "\dt transporte.*"
```

Deberías ver:
```
 transporte | lineas        | table
 transporte | paradas       | table  
 transporte | patterns      | table
 transporte | pattern_stops | table
```

---

### 2. Instalar Dependencias del Scraper

```bash
pip install httpx shapely geoalchemy2
```

---

### 3. Ejecutar Scraper

```bash
# Ejecución simple
python scraper_guia_urbana.py

# Con log en archivo
python scraper_guia_urbana.py 2>&1 | tee scraping_$(date +%Y%m%d_%H%M%S).log
```

**Tiempo estimado:** 5-8 minutos para 132 líneas

---

### 4. Verificar Resultados

```sql
-- Ver líneas creadas
SELECT COUNT(*) FROM transporte.lineas;
-- Esperado: ~45 líneas

-- Ver patterns creados
SELECT COUNT(*) FROM transporte.patterns;
-- Esperado: ~90 patterns (ida + vuelta)

-- Ver paradas creadas
SELECT COUNT(*) FROM transporte.paradas;
-- Esperado: ~1000-1500 paradas

-- Ver ejemplo de ruta completa
SELECT 
    l.nombre,
    p.name as pattern,
    COUNT(ps.id) as num_paradas
FROM transporte.lineas l
JOIN transporte.patterns p ON l.id_linea = p.id_linea
JOIN transporte.pattern_stops ps ON p.id = ps.pattern_id
WHERE l.nombre = '15'
GROUP BY l.nombre, p.name;
```

---

### 5. (Opcional) Ejecutar Tests

```bash
# Instalar pytest si no lo tienes
pip install pytest pytest-asyncio

# Ejecutar tests
pytest tests/test_scraper.py -v
```

---

## 📁 Archivos Creados

```
backend/
├── app/models/
│   ├── line.py           ← Modificado (+ campos trufi-core)
│   ├── stop.py           ← Modificado (nombre_parada)
│   ├── pattern.py        ← NUEVO
│   ├── pattern_stop.py   ← NUEVO
│   └── __init__.py       ← Actualizado
├── migrations/
│   └── 001_trufi_core_schema.sql  ← NUEVO
├── scraper_guia_urbana.py         ← NUEVO
└── tests/
    └── test_scraper.py            ← NUEVO
```

---

## ❓ Troubleshooting

**Error: "No module named 'geoalchemy2'"**
```bash
pip install geoalchemy2 shapely
```

**Error: "Could not connect to database"**
```bash
# Verificar PostgreSQL
pg_isready

# Revisar .env
cat .env | grep DATABASE_URL
```

**Error: "relation transporte.patterns does not exist"**
```bash
# Ejecutar migración primero
psql -U postgres -d transporte_db -f migrations/001_trufi_core_schema.sql
```

---

## 📊 Resultado Esperado

```
==================================================================
📊 REPORTE FINAL DE SCRAPING
==================================================================
✅ Rutas exitosas:     48
❌ Rutas fallidas:     84
🚍 Líneas creadas:     45
🛣️  Patterns creados:   90
📍 Paradas creadas:    1250
==================================================================
```

---

## ✅ Siguiente Paso

Una vez completado:

1. ✅ Verifica datos en BD con las queries arriba
2. ⏭️ Continúa con **Fase 2**: Implementar endpoint `/plan`

Ver documentación completa en: `FASE_0_1_DOCUMENTACION.md`
