from sqlalchemy import Column, Integer, String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class PatternStop(Base):
    """
    Asociación entre Pattern y Stop con orden de secuencia
    Representa las paradas de una ruta en orden
    """
    __tablename__ = "pattern_stops"
    __table_args__ = (
        UniqueConstraint('pattern_id', 'id_parada', 'sequence', name='uq_pattern_stop_sequence'),
        Index('idx_pattern_stops_pattern', 'pattern_id'),
        Index('idx_pattern_stops_parada', 'id_parada'),
        {'schema': 'transporte'}
    )
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(String(50), ForeignKey('transporte.patterns.id', ondelete='CASCADE'), nullable=False)
    id_parada = Column(Integer, ForeignKey('transporte.paradas.id_parada', ondelete='CASCADE'), nullable=False)
    sequence = Column(Integer, nullable=False)  # Orden en la secuencia (1, 2, 3, ...)
    
    # Relaciones
    pattern = relationship("Pattern", back_populates="stops")
    parada = relationship("Stop")
    
    def __repr__(self):
        return f"<PatternStop(pattern='{self.pattern_id}', stop={self.id_parada}, seq={self.sequence})>"
