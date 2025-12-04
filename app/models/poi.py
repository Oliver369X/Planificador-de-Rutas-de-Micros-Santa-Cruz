"""
Modelo para Puntos de Interés (POIs) genérico
Consolida: salud, seguridad, educación, transporte, infraestructura
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.database import Base

class PointOfInterest(Base):
    """
    Punto de Interés genérico para toda la ciudad
    
    Tipos soportados:
    - salud: hospitales, clínicas, centros de salud
    - seguridad: estaciones policiales, bomberos
    - educacion: colegios, universidades, institutos
    - transporte: paradas, oficinas, terminales
    - infraestructura: parques, plazas, centros culturales
    """
    __tablename__ = "points_of_interest"
    __table_args__ = {'schema': 'transporte'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Campos de identificación
    objectid = Column(Integer, unique=True, index=True)  # ID del API municipal
    nombre = Column(String(255), nullable=False, index=True)
    tipo = Column(String(50), nullable=False, index=True)  # salud, seguridad, educacion, etc.
    subtipo = Column(String(100), nullable=True)  # Hospital 2do nivel, Estación Policial, etc.
    
    # Ubicación
    latitud = Column(String(20), nullable=False)
    longitud = Column(String(20), nullable=False)
    geom = Column(Geometry('POINT', srid=4326), nullable=True)
    
    # Información adicional
    direccion = Column(String(500), nullable=True)
    telefono = Column(String(100), nullable=True)
    horario = Column(String(200), nullable=True)
    distrito = Column(String(50), nullable=True)
    
    # Datos flexibles (JSON)
    # 'metadata' es reservado en SQLAlchemy, mapeamos a la columna 'metadata'
    poi_metadata = Column("metadata", JSON, nullable=True)
    
    # Control
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<POI(id={self.id}, tipo='{self.tipo}', nombre='{self.nombre}')>"
