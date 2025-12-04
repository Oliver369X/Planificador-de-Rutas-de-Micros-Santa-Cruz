import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Agregar root al path (3 niveles arriba desde tests/manual)
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import engine
from sqlalchemy import text
import random

load_dotenv()

def test_auth_manual():
    print("🔧 Iniciando prueba manual de Autenticación...")
    
    client = TestClient(app)
    
    # Generar usuario aleatorio
    rand_id = random.randint(1000, 9999)
    email = f"test_user_{rand_id}@example.com"
    password = "password123"
    nombre = f"Test User {rand_id}"
    
    print(f"👤 Usuario de prueba: {email}")
    
    # 1. Registro
    print("\n📝 Probando Registro (/api/v1/auth/register)...")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "nombre": nombre,
            "correo": email,
            "contraseña": password,
            "rol": "Usuario"
        }
    )
    
    if response.status_code == 200:
        print("✅ Registro exitoso")
        user_data = response.json()
        print(f"   ID: {user_data.get('id_usuario')}")
    else:
        print(f"❌ Error en registro: {response.status_code}")
        print(response.text)
        return

    # 2. Login
    print("\n🔑 Probando Login (/api/v1/auth/login)...")
    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": email,
            "contraseña": password
        }
    )
    
    if response.status_code == 200:
        print("✅ Login exitoso")
        data = response.json()
        token = data.get("access_token")
        print(f"   Token: {token[:20]}...")
    else:
        print(f"❌ Error en login: {response.status_code}")
        print(response.text)
        return

    # Limpieza (Opcional, pero bueno para no llenar la BD de basura)
    # print("\n🧹 Limpiando usuario de prueba...")
    # with engine.connect() as conn:
    #     conn.execute(text("DELETE FROM transporte.usuarios WHERE correo = :email"), {"email": email})
    #     conn.commit()
    # print("✅ Limpieza completada")

if __name__ == "__main__":
    test_auth_manual()
