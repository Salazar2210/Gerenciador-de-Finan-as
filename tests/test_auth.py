def test_register_success(client, db):
    payload = {
        "email": "usuario@exemplo.com",
        "password": "senha123",
        "full_name": "Usuário Exemplo",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "usuario@exemplo.com"
    assert data["full_name"] == "Usuário Exemplo"
    assert "senha" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client, db):
    payload = {
        "email": "usuario@exemplo.com",
        "password": "senha123",
        "full_name": "Usuário Exemplo",
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409, response.text
    assert "detail" in response.json()


def test_register_email_is_lowercased(client, db):
    payload = {
        "email": "USUARIO@EXEMPLO.COM",
        "password": "senha123",
        "full_name": "Usuário Exemplo",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "usuario@exemplo.com"


def test_login_success(client, db):
    payload = {
        "email": "usuario@exemplo.com",
        "password": "senha123",
        "full_name": "Usuário Exemplo",
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "usuario@exemplo.com", "password": "senha123"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, db):
    payload = {
        "email": "usuario@exemplo.com",
        "password": "senha123",
        "full_name": "Usuário Exemplo",
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "usuario@exemplo.com", "password": "senhaerrada"},
    )
    assert response.status_code == 401, response.text


def test_login_unknown_email(client, db):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "naoexiste@exemplo.com", "password": "senha123"},
    )
    assert response.status_code == 401, response.text


def test_users_me_without_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_users_me_with_invalid_token(client):
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer token-invalido"})
    assert response.status_code == 401


def test_users_me_success(client, db):
    payload = {
        "email": "usuario@exemplo.com",
        "password": "senha123",
        "full_name": "Usuário Exemplo",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "usuario@exemplo.com", "password": "senha123"},
    )
    token = login.json()["access_token"]
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "usuario@exemplo.com"
