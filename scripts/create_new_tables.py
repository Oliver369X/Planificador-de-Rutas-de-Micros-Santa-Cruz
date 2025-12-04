import sys
import os
from pathlib import Path

# Agregar root al path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import Base, engine
# Importar todos los modelos para que se registren
from app.models import *

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
