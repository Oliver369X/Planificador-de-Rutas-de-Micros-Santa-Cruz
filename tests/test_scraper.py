"""
Tests para el scraper de Guía Urbana Municipal
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper_guia_urbana import GuiaUrbanaScraper, GUIA_URBANA_BASE
from app.models import Base, Line, Pattern, PatternStop, Stop

# Test database (SQLite en memoria)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    """Crea una base de datos de prueba"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    
    TestSessionLocal = sessionmaker(bind=engine)
    db = TestSessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def scraper(test_db):
    """Crea instancia del scraper con BD de prueba"""
    return GuiaUrbanaScraper(test_db)

# Mock de respuesta de API
MOCK_GEOJSON_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": 30,
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [
                    [
                        [-63.1821, -17.7834],
                        [-63.1823, -17.7835],
                        [-63.1825, -17.7836]
                    ]
                ]
            },
            "properties": {
                "objectid": 30,
                "nombre": "15",
                "sentido": 1,
                "origen": 5,
                "destino": 11
            }
        }
    ]
}

class TestGuiaUrbanaScraper:
    """Tests para el scraper"""
    
    @pytest.mark.asyncio
    async def test_fetch_ruta_success(self, scraper):
        """Test: Obtener ruta exitosamente"""
        with patch.object(scraper.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GEOJSON_RESPONSE
            mock_get.return_value = mock_response
            
            result = await scraper.fetch_ruta(15)
            
            assert result is not None
            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1
    
    @pytest.mark.asyncio
    async def test_fetch_ruta_404(self, scraper):
        """Test: Ruta no encontrada"""
        with patch.object(scraper.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = await scraper.fetch_ruta(999)
            
            assert result is None
    
    def test_extract_routes_from_geojson(self, scraper):
        """Test: Extraer rutas de GeoJSON"""
        routes = scraper.extract_routes_from_geojson(MOCK_GEOJSON_RESPONSE)
        
        assert len(routes) == 1
        assert routes[0]["nombre"] == "15"
        assert routes[0]["sentido"] == 1
        assert "geometry" in routes[0]
    
    def test_create_or_get_line(self, scraper, test_db):
        """Test: Crear línea nueva"""
        line = scraper.create_or_get_line("15")
        
        assert line is not None
        assert line.nombre == "15"
        assert line.short_name == "15"
        assert line.long_name == "Línea 15"
        assert line.color == "0088FF"
        assert line.mode == "BUS"
        assert scraper.stats["lineas_creadas"] == 1
    
    def test_create_or_get_line_existing(self, scraper, test_db):
        """Test: Obtener línea existente"""
        # Crear línea primera vez
        line1 = scraper.create_or_get_line("15")
        stats_after_first = scraper.stats["lineas_creadas"]
        
        # Intentar crear de nuevo
        line2 = scraper.create_or_get_line("15")
        
        assert line1.id_linea == line2.id_linea
        assert scraper.stats["lineas_creadas"] == stats_after_first  # No aumentó
    
    def test_convert_geometry_to_linestring(self, scraper):
        """Test: Convertir MultiLineString a LineString"""
        geometry = {
            "type": "MultiLineString",
            "coordinates": [
                [
                    [-63.1821, -17.7834],
                    [-63.1823, -17.7835]
                ]
            ]
        }
        
        result = scraper.convert_geometry_to_linestring(geometry)
        
        assert result is not None
    
    def test_convert_geometry_invalid(self, scraper):
        """Test: Geometría inválida"""
        geometry = {"type": "Point", "coordinates": [0, 0]}
        
        result = scraper.convert_geometry_to_linestring(geometry)
        
        assert result is None
    
    def test_create_pattern(self, scraper, test_db):
        """Test: Crear pattern"""
        line = scraper.create_or_get_line("15")
        
        geometry = {
            "type": "MultiLineString",
            "coordinates": [[
                [-63.1821, -17.7834],
                [-63.1823, -17.7835]
            ]]
        }
        
        pattern = scraper.create_pattern(
            line=line,
            nombre_ruta="15",
            sentido=1,
            geometry=geometry,
            objectid=30
        )
        
        assert pattern is not None
        assert pattern.id == f"pattern:{line.id_linea}:ida"
        assert pattern.name == "15 - Ida"
        assert pattern.sentido == "ida"
        assert scraper.stats["patterns_creados"] == 1
    
    @pytest.mark.asyncio
    async def test_scrape_route_integration(self, scraper):
        """Test de integración: Scrape completo de una ruta"""
        with patch.object(scraper.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GEOJSON_RESPONSE
            mock_get.return_value = mock_response
            
            await scraper.scrape_route(15)
            
            assert scraper.stats["rutas_exitosas"] == 1
            assert scraper.stats["lineas_creadas"] == 1
            assert scraper.stats["patterns_creados"] == 1

def test_stats_initialization(scraper):
    """Test: Estadísticas inicializadas correctamente"""
    assert scraper.stats["rutas_exitosas"] == 0
    assert scraper.stats["rutas_fallidas"] == 0
    assert scraper.stats["lineas_creadas"] == 0
    assert scraper.stats["patterns_creados"] == 0
    assert scraper.stats["paradas_creadas"] == 0
    assert len(scraper.stats["errores"]) == 0

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
