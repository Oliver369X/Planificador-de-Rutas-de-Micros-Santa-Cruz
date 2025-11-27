from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime, func, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class PaymentTypeEnum(str, enum.Enum):
    RECARGA = "Recarga"
    PASAJE = "Pasaje"

class Payment(Base):
    __tablename__ = "pagos"
    __table_args__ = {'schema': 'transporte'}
    
    id_pago = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey('transporte.usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    tipo = Column(Enum(PaymentTypeEnum), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)  # Bs.
    descripcion = Column(String(255), nullable=True)
    fecha_hora = Column(DateTime, server_default=func.now())
    
    # Relaciones
    usuario = relationship("User", back_populates="pagos")
