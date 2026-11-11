def _register_and_login(client, email="a@exemplo.com", password="senha123"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "User A"},
    )
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    return r.json()["access_token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_accounts(client, db):
    token = _register_and_login(client)
    r = client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "100.00"},
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Carteira"
    assert data["balance"] == "100.00"
    assert data["initial_balance"] == "100.00"

    r = client.get("/api/v1/accounts", headers=_auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_account_balance_calculated(client, db):
    token = _register_and_login(client)
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "1000.00"},
        headers=_auth_header(token),
    )
    cat = client.post(
        "/api/v1/categories",
        json={"name": "Salário", "type": "INCOME"},
        headers=_auth_header(token),
    ).json()
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    cat2 = client.post(
        "/api/v1/categories",
        json={"name": "Mercado", "type": "EXPENSE"},
        headers=_auth_header(token),
    ).json()
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat2["id"],
            "type": "EXPENSE",
            "amount": "200.00",
            "date": "2026-01-15",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/accounts/1", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["balance"] == "1300.00"


def test_account_name_unique_case_insensitive(client, db):
    token = _register_and_login(client)
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    r = client.post(
        "/api/v1/accounts",
        json={"name": "CARTEIRA", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    assert r.status_code == 409, r.text


def test_account_isolation_404(client, db):
    token_a = _register_and_login(client, email="a@exemplo.com")
    token_b = _register_and_login(client, email="b@exemplo.com")
    client.post(
        "/api/v1/accounts",
        json={"name": "Conta A", "initial_balance": "0.00"},
        headers=_auth_header(token_a),
    )
    # usuário B tenta ler conta do A
    r = client.get("/api/v1/accounts/1", headers=_auth_header(token_b))
    assert r.status_code == 404, r.text
    # usuário B tenta alterar
    r = client.patch(
        "/api/v1/accounts/1",
        json={"name": "X"},
        headers=_auth_header(token_b),
    )
    assert r.status_code == 404, r.text
    # usuário B tenta excluir
    r = client.delete("/api/v1/accounts/1", headers=_auth_header(token_b))
    assert r.status_code == 404, r.text


def test_create_and_list_categories(client, db):
    token = _register_and_login(client)
    r = client.post(
        "/api/v1/categories",
        json={"name": "Salário", "type": "INCOME"},
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.text
    r = client.get("/api/v1/categories", headers=_auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_category_filter_by_type(client, db):
    token = _register_and_login(client)
    client.post(
        "/api/v1/categories",
        json={"name": "Salário", "type": "INCOME"},
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/categories",
        json={"name": "Mercado", "type": "EXPENSE"},
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/categories?type=EXPENSE", headers=_auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Mercado"


def test_category_type_immutable(client, db):
    token = _register_and_login(client)
    cat = client.post(
        "/api/v1/categories",
        json={"name": "Salário", "type": "INCOME"},
        headers=_auth_header(token),
    ).json()
    r = client.patch(
        f"/api/v1/categories/{cat['id']}",
        json={"name": "Salário", "type": "EXPENSE"},
        headers=_auth_header(token),
    )
    # schema de update só aceita name; type não muda. Verifica que continua INCOME.
    r = client.get(f"/api/v1/categories/{cat['id']}", headers=_auth_header(token))
    assert r.json()["type"] == "INCOME"


def test_category_unique_name_type_case_insensitive(client, db):
    token = _register_and_login(client)
    client.post(
        "/api/v1/categories",
        json={"name": "Mercado", "type": "EXPENSE"},
        headers=_auth_header(token),
    )
    r = client.post(
        "/api/v1/categories",
        json={"name": "MERCADO", "type": "EXPENSE"},
        headers=_auth_header(token),
    )
    assert r.status_code == 409, r.text


def test_delete_category_without_transactions(client, db):
    token = _register_and_login(client)
    cat = client.post(
        "/api/v1/categories",
        json={"name": "Lazer", "type": "EXPENSE"},
        headers=_auth_header(token),
    ).json()
    r = client.delete(f"/api/v1/categories/{cat['id']}", headers=_auth_header(token))
    assert r.status_code == 204, r.text


def test_category_isolation_404(client, db):
    token_a = _register_and_login(client, email="a@exemplo.com")
    token_b = _register_and_login(client, email="b@exemplo.com")
    client.post(
        "/api/v1/categories",
        json={"name": "Cat A", "type": "EXPENSE"},
        headers=_auth_header(token_a),
    )
    r = client.get("/api/v1/categories/1", headers=_auth_header(token_b))
    assert r.status_code == 404, r.text
