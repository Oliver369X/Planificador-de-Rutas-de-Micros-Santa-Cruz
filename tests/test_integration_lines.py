import pytest
from app.models.line import Line
from app.models.user import User
from app.services.auth_service import AuthService

@pytest.fixture
def admin_user(db):
    password = "adminpassword"
    hashed = AuthService.hash_password(password)
    user = User(nombre="Admin User", correo="admin@example.com", contraseña=hashed, rol="Administrador")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_token(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"correo": "admin@example.com", "contraseña": "adminpassword"})
    return response.json()["access_token"]

def test_create_line(client, db, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/lines/", json={"nombre": "Linea 10", "descripcion": "Ruta norte"}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Linea 10"
    
    # Verify in DB
    line = db.query(Line).filter(Line.nombre == "Linea 10").first()
    assert line is not None

def test_get_lines(client, db):
    # Setup
    line1 = Line(nombre="Linea A", descripcion="Desc A")
    line2 = Line(nombre="Linea B", descripcion="Desc B")
    db.add_all([line1, line2])
    db.commit()
    
    response = client.get("/api/v1/lines/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = [l["nombre"] for l in data]
    assert "Linea A" in names
    assert "Linea B" in names
