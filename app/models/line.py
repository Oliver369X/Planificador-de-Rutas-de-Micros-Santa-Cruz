from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base

class Line(Base):
    __tablename__ = "lineas"
    __table_args__ = {'schema': 'transporte'}
    
    id_linea = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    
    # Campos para compatibilidad trufi-core
    short_name = Column(String(10), nullable=True)  # Nombre corto: "1", "15", "27 rojo"
    long_name = Column(String(255), nullable=True)  # Nombre descriptivo completo
    color = Column(String(6), nullable=True, default="0088FF")  # Hex sin #
    text_color = Column(String(6), nullable=True, default="FFFFFF")  # Hex sin #
    mode = Column(String(20), nullable=True, default="BUS")  # BUS, TRAM, RAIL, etc.
    
    # Campos existentes
    descripcion = Column(String(255), nullable=True)
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    # Relaciones
    patterns = relationship("Pattern", back_populates="linea", cascade="all, delete-orphan")
    recorridos = relationship("Route", back_populates="linea", cascade="all, delete-orphan")
    trasbordos_origen = relationship("Transfer", foreign_keys="Transfer.id_linea_origen", back_populates="linea_origen")
    trasbordos_destino = relationship("Transfer", foreign_keys="Transfer.id_linea_destino", back_populates="linea_destino")
