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

def test_crud_manual():
    print("🔧 Probando CRUDs Adicionales...")
    
    client = TestClient(app)
    
    # 1. Login para obtener token
    rand_id = random.randint(1000, 9999)
    email = f"crud_test_{rand_id}@example.com"
    password = "password123"
    
    # Registrar usuario
    client.post("/api/v1/auth/register", json={
        "nombre": "CRUD Tester",
        "correo": email,
        "contraseña": password,
        "rol": "Usuario"
    })
    
    # Login
    login_resp = client.post("/api/v1/auth/login", json={
        "correo": email,
        "contraseña": password
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login exitoso")

    # 2. Test /users/me
    print("\n👤 Probando GET /users/me...")
    resp = client.get("/api/v1/users/me", headers=headers)
    if resp.status_code == 200:
        print(f"✅ User Profile: {resp.json()['correo']}")
    else:
        print(f"❌ Error Profile: {resp.status_code}")

    # 3. Test Favorites
    print("\n⭐ Probando Favoritos...")
    # Crear
    fav_data = {
        "nombre": "Casa",
        "direccion": "Av. Banzer 4to Anillo",
        "latitud": "-17.75",
        "longitud": "-63.17"
    }
    resp = client.post("/api/v1/favorites/", json=fav_data, headers=headers)
    if resp.status_code == 200:
        fav_id = resp.json()["id"]
        print(f"✅ Favorito creado (ID: {fav_id})")
        
        # Listar
        resp = client.get("/api/v1/favorites/", headers=headers)
        print(f"✅ Lista Favoritos: {len(resp.json())}")
        
        # Borrar
        client.delete(f"/api/v1/favorites/{fav_id}", headers=headers)
        print("✅ Favorito eliminado")
    else:
        print(f"❌ Error Favoritos: {resp.status_code}")
        print(resp.text)

    # 4. Test Reports
    print("\n📢 Probando Reportes...")
    rep_data = {
        "tipo": "Ruta incorrecta",
        "descripcion": "La línea 41 no pasa por aquí",
        "latitud": "-17.78",
        "longitud": "-63.18"
    }
    resp = client.post("/api/v1/reports/", json=rep_data, headers=headers)
    if resp.status_code == 200:
        print(f"✅ Reporte creado (ID: {resp.json()['id']})")
    else:
        print(f"❌ Error Reportes: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    test_crud_manual()
