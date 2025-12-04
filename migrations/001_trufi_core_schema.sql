-- Migración Trufi-Core: Agregar campos, patterns y pattern_stops

-- 1. Agregar campos a líneas para trufi-core
ALTER TABLE transporte.lineas 
ADD COLUMN IF NOT EXISTS short_name VARCHAR(10),
ADD COLUMN IF NOT EXISTS long_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS text_color VARCHAR(6) DEFAULT 'FFFFFF',
ADD COLUMN IF NOT EXISTS mode VARCHAR(20) DEFAULT 'BUS';

-- Modificar columna color (cambiar de VARCHAR(20) a VARCHAR(6))
ALTER TABLE transporte.lineas ALTER COLUMN color TYPE VARCHAR(6);
ALTER TABLE transporte.lineas ALTER COLUMN color SET DEFAULT '0088FF';

-- 2. Crear tabla patterns
CREATE TABLE IF NOT EXISTS transporte.patterns (
    id VARCHAR(50) PRIMARY KEY,
    code VARCHAR(20),
    name VARCHAR(255) NOT NULL,
    id_linea INTEGER REFERENCES transporte.lineas(id_linea) ON DELETE CASCADE NOT NULL,
    sentido VARCHAR(10) NOT NULL CHECK (sentido IN ('ida', 'vuelta')),
    geometry geometry(LINESTRING, 4326)
);

-- Índices para patterns
CREATE INDEX IF NOT EXISTS idx_pattern_linea ON transporte.patterns(id_linea);
CREATE INDEX IF NOT EXISTS idx_patterns_geometry ON transporte.patterns USING GIST(geometry);

-- Crear tabla pattern_stops
CREATE TABLE IF NOT EXISTS transporte.pattern_stops (
    id SERIAL PRIMARY KEY,
    pattern_id VARCHAR(50) NOT NULL,
    id_parada INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    CONSTRAINT uq_pattern_stop_sequence UNIQUE(pattern_id, id_parada, sequence),
    CONSTRAINT fk_pattern FOREIGN KEY (pattern_id) REFERENCES transporte.patterns(id) ON DELETE CASCADE,
    CONSTRAINT fk_parada FOREIGN KEY (id_parada) REFERENCES transporte.paradas(id_parada) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pattern_stops_pattern ON transporte.pattern_stops(pattern_id);
CREATE INDEX IF NOT EXISTS idx_pattern_stops_parada ON transporte.pattern_stops(id_parada);

-- Actualizar short_name y long_name de líneas existentes
UPDATE transporte.lineas 
SET short_name = nombre,
    long_name = CONCAT('Línea ', nombre)
WHERE short_name IS NULL;
