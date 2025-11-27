import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# --- MOCKING DEPENDENCIES BEFORE IMPORTS ---
mock_geoalchemy2 = MagicMock()
sys.modules["geoalchemy2"] = mock_geoalchemy2
sys.modules["geoalchemy2.types"] = MagicMock()

mock_psycopg2 = MagicMock()
sys.modules["psycopg2"] = mock_psycopg2

mock_sqlalchemy_postgres = MagicMock()
sys.modules["sqlalchemy.dialects.postgresql"] = mock_sqlalchemy_postgres

# --- SET ENV VARS BEFORE IMPORTING CONFIG ---
os.environ["DATABASE_URL"] = "postgresql://user:password@localhost/test_db"

# --- IMPORTS ---
from app.main import app
from app.database import get_db
from app.models.user import User

# --- FIXTURES & OVERRIDES ---
def override_get_db():
    try:
        db = MagicMock()
        yield db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# --- TESTS ---

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Planificador Rutas Micros SC API"}

def test_login_success():
    mock_user = User(id_usuario=1, correo="test@example.com", contraseña="hashed_password", rol="Usuario")
    
    with patch("app.crud.user.crud_user.get_by_email", return_value=mock_user):
        with patch("app.services.auth_service.AuthService.verify_password", return_value=True):
            with patch("app.services.auth_service.AuthService.create_access_token", return_value="mock_token"):
                response = client.post("/api/v1/auth/login", json={"correo": "test@example.com", "contraseña": "password"})
                assert response.status_code == 200
                assert "access_token" in response.json()

def test_login_failure_wrong_password():
    mock_user = User(id_usuario=1, correo="test@example.com", contraseña="hashed_password", rol="Usuario")
    
    with patch("app.crud.user.crud_user.get_by_email", return_value=mock_user):
        with patch("app.services.auth_service.AuthService.verify_password", return_value=False):
            response = client.post("/api/v1/auth/login", json={"correo": "test@example.com", "contraseña": "wrong_password"})
            assert response.status_code == 401

def test_login_failure_user_not_found():
    with patch("app.crud.user.crud_user.get_by_email", return_value=None):
        response = client.post("/api/v1/auth/login", json={"correo": "nonexistent@example.com", "contraseña": "password"})
        assert response.status_code == 401

def test_get_lines_empty():
    with patch("app.crud.line.crud_line.get_all_active", return_value=[]):
        response = client.get("/api/v1/lines/")
        assert response.status_code == 200
        assert response.json() == []

def test_create_line_unauthorized():
    response = client.post("/api/v1/lines/", json={"nombre": "Linea 1"})
    assert response.status_code == 401
