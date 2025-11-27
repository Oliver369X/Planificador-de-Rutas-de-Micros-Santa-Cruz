from sqlalchemy import Column, Integer, String, Enum, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class RoleEnum(str, enum.Enum):
    ADMIN = "Administrador"
    USER = "Usuario"

class User(Base):
    __tablename__ = "usuarios"
    __table_args__ = {'schema': 'transporte'}
    
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(100), unique=True, nullable=False, index=True)
    contraseña = Column(String(255), nullable=False)
    rol = Column(Enum(RoleEnum), default=RoleEnum.USER, nullable=False)
    saldo = Column(Integer, default=0)  # En centavos (Bs. * 100)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    # Relaciones
    viajes = relationship("Trip", back_populates="usuario")
    pagos = relationship("Payment", back_populates="usuario")
