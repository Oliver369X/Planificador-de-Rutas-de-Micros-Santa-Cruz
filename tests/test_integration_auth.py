import pytest
from app.models.user import User
from app.services.auth_service import AuthService

def test_login_success(client, db):
    # Setup: Create a user in the DB
    password = "testpassword"
    hashed = AuthService.hash_password(password)
    user = User(nombre="Test User", correo="test_auth@example.com", contraseña=hashed, rol="Usuario")
    db.add(user)
    db.commit()
    
    response = client.post("/api/v1/auth/login", json={"correo": "test_auth@example.com", "contraseña": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure_wrong_password(client, db):
    # Setup
    password = "testpassword"
    hashed = AuthService.hash_password(password)
    user = User(nombre="Test User", correo="test_auth_fail@example.com", contraseña=hashed, rol="Usuario")
    db.add(user)
    db.commit()
    
    response = client.post("/api/v1/auth/login", json={"correo": "test_auth_fail@example.com", "contraseña": "wrong"})
    assert response.status_code == 401

def test_login_failure_user_not_found(client):
    response = client.post("/api/v1/auth/login", json={"correo": "nonexistent@example.com", "contraseña": "password"})
    assert response.status_code == 401
