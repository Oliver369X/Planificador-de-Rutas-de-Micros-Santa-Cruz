from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base

class Pattern(Base):
    """
    Patrón de ruta - Representa un recorrido específico de una línea
    Compatible con trufi-core GraphQL/REST queries
    
    Ejemplo: Línea 15 tiene 2 patterns:
    - pattern:15:ida (sentido ida)
    - pattern:15:vuelta (sentido vuelta)
    """
    __tablename__ = "patterns"
    __table_args__ = (
        Index('idx_pattern_linea', 'id_linea'),
        {'schema': 'transporte'}
    )
    
    id = Column(String(50), primary_key=True)  # Ej: "pattern:15:ida"
    code = Column(String(20), nullable=True)   # Código corto: "15"
    name = Column(String(255), nullable=False)  # "Línea 15 - Ida"
    id_linea = Column(Integer, ForeignKey('transporte.lineas.id_linea', ondelete='CASCADE'), nullable=False)
    sentido = Column(String(10), nullable=False)  # 'ida' o 'vuelta'
    
    # Geometría de la ruta completa (LineString)
    geometry = Column(Geometry('LINESTRING', srid=4326), nullable=True)
    
    # Relaciones
    linea = relationship("Line", back_populates="patterns")
    stops = relationship("PatternStop", back_populates="pattern", 
                        order_by="PatternStop.sequence", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Pattern(id='{self.id}', name='{self.name}')>"
