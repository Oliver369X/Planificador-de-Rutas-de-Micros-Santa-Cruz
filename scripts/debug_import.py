import sys
import os
sys.path.append(os.getcwd())
try:
    from app.crud.user import crud_user
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
