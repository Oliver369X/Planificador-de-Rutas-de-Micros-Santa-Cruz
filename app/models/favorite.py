from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Favorite(Base):
    __tablename__ = "favoritos"
    __table_args__ = {'schema': 'transporte'}
    
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("transporte.usuarios.id_usuario"), nullable=False)
    nombre = Column(String(100), nullable=False)  # "Casa", "Trabajo"
    direccion = Column(String(255), nullable=True)
    latitud = Column(String(20), nullable=False)
    longitud = Column(String(20), nullable=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    usuario = relationship("User", back_populates="favoritos")
