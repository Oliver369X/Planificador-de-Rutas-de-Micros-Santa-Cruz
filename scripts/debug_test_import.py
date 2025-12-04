import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

print("Attempting to import app.main...")
try:
    from app.main import app
    print("Success: app.main")
except Exception as e:
    print(f"Failed: app.main - {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import tests.conftest...")
try:
    import tests.conftest
    print("Success: tests.conftest")
except Exception as e:
    print(f"Failed: tests.conftest - {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import tests.test_integration_auth...")
try:
    import tests.test_integration_auth
    print("Success: tests.test_integration_auth")
except Exception as e:
    print(f"Failed: tests.test_integration_auth - {e}")
    import traceback
    traceback.print_exc()
