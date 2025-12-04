from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Report(Base):
    __tablename__ = "reportes"
    __table_args__ = {'schema': 'transporte'}
    
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("transporte.usuarios.id_usuario"), nullable=True) # Puede ser anónimo
    tipo = Column(String(50), nullable=False) # "Ruta incorrecta", "Parada inexistente", "Otro"
    descripcion = Column(Text, nullable=False)
    latitud = Column(String(20), nullable=True)
    longitud = Column(String(20), nullable=True)
    resuelto = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    usuario = relationship("User", back_populates="reportes")
