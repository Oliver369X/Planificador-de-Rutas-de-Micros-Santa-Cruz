from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Transfer(Base):
    __tablename__ = "trasbordos"
    __table_args__ = {'schema': 'transporte'}
    
    id_trasbordo = Column(Integer, primary_key=True, index=True)
    id_viaje = Column(Integer, ForeignKey('transporte.viajes.id_viaje', ondelete='CASCADE'), nullable=False)
    id_linea_origen = Column(Integer, ForeignKey('transporte.lineas.id_linea'), nullable=False)
    id_linea_destino = Column(Integer, ForeignKey('transporte.lineas.id_linea'), nullable=False)
    id_parada = Column(Integer, ForeignKey('transporte.paradas.id_parada'), nullable=False)
    tiempo_estimado_trasbordo = Column(Integer, nullable=True)  # minutos de espera
    
    # Relaciones
    viaje = relationship("Trip", back_populates="trasbordos")
    linea_origen = relationship("Line", foreign_keys=[id_linea_origen], back_populates="trasbordos_origen")
    linea_destino = relationship("Line", foreign_keys=[id_linea_destino], back_populates="trasbordos_destino")
    parada = relationship("Stop", back_populates="trasbordos")
