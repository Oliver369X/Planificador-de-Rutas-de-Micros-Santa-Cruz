from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Line(Base):
    __tablename__ = "lineas"
    __table_args__ = {'schema': 'transporte'}
    
    id_linea = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
    color = Column(String(20), nullable=True)
    descripcion = Column(String(255), nullable=True)
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    # Relaciones
    recorridos = relationship("Route", back_populates="linea", cascade="all, delete-orphan")
    trasbordos_origen = relationship("Transfer", foreign_keys="Transfer.id_linea_origen", back_populates="linea_origen")
    trasbordos_destino = relationship("Transfer", foreign_keys="Transfer.id_linea_destino", back_populates="linea_destino")
