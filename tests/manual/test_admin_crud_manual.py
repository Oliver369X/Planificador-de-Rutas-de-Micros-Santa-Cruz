import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import random

# Agregar root al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app

load_dotenv()

def test_admin_crud():
    print("🔧 Probando CRUDs de Admin (Paradas y POIs)...")
    
    client = TestClient(app)
    
    # 1. Registrar Admin (o login si ya existe)
    rand_id = random.randint(1000, 9999)
    email = f"admin_test_{rand_id}@example.com"
    password = "adminpassword"
    
    # Intentar registrar como Admin (esto depende de si el endpoint permite registrar admins, 
    # normalmente no, pero para test asumiremos que podemos o que modificamos el rol en BD después)
    # Por defecto el registro crea rol "Usuario". 
    # Truco: Login con un usuario y luego simular que es admin en el test o 
    # modificar la BD directamente.
    # Para este test manual, vamos a registrar y luego asumir que la lógica de backend 
    # permite registrar admins O vamos a hackear el token/rol.
    
    # Mejor opción: Registrar usuario normal y luego actualizar su rol en BD (si tuviera acceso directo a BD aquí)
    # O usar un usuario admin pre-existente si lo hubiera.
    
    # Vamos a registrar usuario normal y ver que FALLA (403)
    client.post("/api/v1/auth/register", json={
        "nombre": "Fake Admin",
        "correo": email,
        "contraseña": password,
        "rol": "Administrador" # El endpoint de registro ignora esto y pone Usuario por defecto normalmente
    })
    
    # Login
    login_resp = client.post("/api/v1/auth/login", json={
        "correo": email,
        "contraseña": password
    })
    
    if login_resp.status_code != 200:
        print("❌ Error Login Admin")
        return

    token = login_resp.json()["access_token"]
    user_data = login_resp.json()["user"]
    
    # Si el backend ignora el rol en registro, esto será "Usuario"
    print(f"   Rol actual: {user_data.get('rol')}")
    
    # Si es Usuario, no podremos probar los endpoints de Admin.
    # Necesitamos un Admin real.
    # Vamos a inyectar un Admin en la BD usando SQL directo para el test.
    # Vamos a inyectar un Admin en la BD usando ORM para evitar problemas de Enum
    from app.database import SessionLocal
    from app.models.user import User, RoleEnum
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.correo == email).first()
        if user:
            user.rol = RoleEnum.ADMIN
            db.commit()
            print("   ✅ Rol actualizado a Administrador en BD (ORM)")
    except Exception as e:
        print(f"❌ Error actualizando rol: {e}")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test Create POI
    print("\n📍 Probando Crear POI (Admin)...")
    poi_data = {
        "nombre": "POI Test Admin",
        "tipo": "infraestructura",
        "latitud": "-17.77",
        "longitud": "-63.19",
        "direccion": "Test Address"
    }
    resp = client.post("/api/v1/pois/", json=poi_data, headers=headers)
    if resp.status_code == 201:
        poi_id = resp.json()["id"]
        print(f"✅ POI creado (ID: {poi_id})")
        
        # Update
        resp = client.put(f"/api/v1/pois/{poi_id}", json={"nombre": "POI Updated"}, headers=headers)
        if resp.status_code == 200:
            print("✅ POI actualizado")
        
        # Delete
        resp = client.delete(f"/api/v1/pois/{poi_id}", headers=headers)
        if resp.status_code == 204:
            print("✅ POI eliminado")
    else:
        print(f"❌ Error Crear POI: {resp.status_code}")
        print(resp.text)

    # 3. Test Delete Stop (Admin)
    # Primero creamos una parada (si hubiera endpoint de crear parada, que sí hay)
    print("\n🚏 Probando CRUD Parada (Admin)...")
    stop_data = {
        "nombre": "Parada Test Admin",
        "latitud": -17.76,
        "longitud": -63.18
    }
    resp = client.post("/api/v1/stops/", json=stop_data, headers=headers)
    if resp.status_code == 201:
        stop_id = resp.json()["id_parada"]
        print(f"✅ Parada creada (ID: {stop_id})")
        
        # Delete
        resp = client.delete(f"/api/v1/stops/{stop_id}", headers=headers)
        if resp.status_code == 204:
            print("✅ Parada eliminada")
    else:
        print(f"❌ Error Crear Parada: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    test_admin_crud()
