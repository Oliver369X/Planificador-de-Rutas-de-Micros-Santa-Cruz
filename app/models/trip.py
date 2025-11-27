from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from geoalchemy2 import Geometry

class Trip(Base):
    __tablename__ = "viajes"
    __table_args__ = {'schema': 'transporte'}
    
    id_viaje = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey('transporte.usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    origen_lat = Column(Numeric(10, 7), nullable=False)
    origen_lon = Column(Numeric(10, 7), nullable=False)
    destino_lat = Column(Numeric(10, 7), nullable=False)
    destino_lon = Column(Numeric(10, 7), nullable=False)
    tiempo_estimado_total = Column(Integer, nullable=True)  # minutos
    distancia_total = Column(Numeric(10, 2), nullable=True)  # km
    fecha_hora = Column(DateTime, server_default=func.now())
    completado = Column(Boolean, default=False)
    
    # Relaciones
    usuario = relationship("User", back_populates="viajes")
    trasbordos = relationship("Transfer", back_populates="viaje")
