import sys
import os
from pathlib import Path

# Agregar root al path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import Base, engine
try:
    print("Importing User...")
    from app.models.user import User
    print("Importing Line...")
    from app.models.line import Line
    print("Importing Stop...")
    from app.models.stop import Stop
    print("Importing Pattern...")
    from app.models.pattern import Pattern
    print("Importing PatternStop...")
    from app.models.pattern_stop import PatternStop
    print("Importing POI...")
    from app.models.poi import PointOfInterest
    
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
