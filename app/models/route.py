from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base

class Route(Base):
    __tablename__ = "recorridos"
    __table_args__ = (
        CheckConstraint("sentido IN ('ida', 'vuelta')"),
        Index('idx_linea_sentido_orden', 'id_linea', 'sentido', 'orden'),
        {'schema': 'transporte'}
    )
    
    id_recorrido = Column(Integer, primary_key=True, index=True)
    id_linea = Column(Integer, ForeignKey('transporte.lineas.id_linea', ondelete='CASCADE'), nullable=False)
    id_parada = Column(Integer, ForeignKey('transporte.paradas.id_parada', ondelete='CASCADE'), nullable=False)
    sentido = Column(String(10), nullable=False)  # 'ida' o 'vuelta'
    orden = Column(Integer, nullable=False)       # Posición en la secuencia
    tiempo_estimado = Column(Integer, nullable=True)  # minutos
    
    # Relaciones
    linea = relationship("Line", back_populates="recorridos")
    parada = relationship("Stop", back_populates="recorridos")
