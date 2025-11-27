from sqlalchemy import Column, Integer, String, Float, DateTime, func, Numeric, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from geoalchemy2 import Geometry

class Stop(Base):
    __tablename__ = "paradas"
    __table_args__ = {'schema': 'transporte'}
    
    id_parada = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    latitud = Column(Numeric(10, 7), nullable=False)
    longitud = Column(Numeric(10, 7), nullable=False)
    geom = Column(Geometry('POINT', srid=4326), nullable=True)  # PostGIS
    descripcion = Column(String(255), nullable=True)
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    # Relaciones
    recorridos = relationship("Route", back_populates="parada")
    trasbordos = relationship("Transfer", back_populates="parada")
