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


def _setup_expense_category(client, token):
    return client.post(
        "/api/v1/categories",
        json={"name": "Mercado", "type": "EXPENSE"},
        headers=_auth_header(token),
    ).json()


def test_create_budget_expense_only(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    # categoria INCOME
    cat_inc = client.post(
        "/api/v1/categories",
        json={"name": "Salário", "type": "INCOME"},
        headers=_auth_header(token),
    ).json()
    r = client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "500.00",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_inc["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "500.00",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 422, r.text


def test_budget_duplicate_conflict_409(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "500.00",
        },
        headers=_auth_header(token),
    )
    r = client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "600.00",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 409, r.text


def test_budget_limit_amount_positive(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    r = client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "0",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 422, r.text


def test_budget_status_ok(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_exp["id"],
            "type": "EXPENSE",
            "amount": "200.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/budgets/status?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()[0]
    assert data["status"] == "OK"
    assert data["spent"] == "200.00"
    assert data["limit_amount"] == "1000.00"


def test_budget_status_warning_exactly_80(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_exp["id"],
            "type": "EXPENSE",
            "amount": "800.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/budgets/status?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    data = r.json()[0]
    assert data["status"] == "WARNING"
    assert data["percentage_used"] == "80.00"


def test_budget_status_warning_exactly_100(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_exp["id"],
            "type": "EXPENSE",
            "amount": "1000.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/budgets/status?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    data = r.json()[0]
    assert data["status"] == "WARNING"
    assert data["percentage_used"] == "100.00"


def test_budget_status_exceeded(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_exp["id"],
            "type": "EXPENSE",
            "amount": "1100.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/budgets/status?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    data = r.json()[0]
    assert data["status"] == "EXCEEDED"


def test_budget_status_filters_year_month(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 2,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/budgets/status?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_delete_category_removes_budget(client, db):
    token = _register_and_login(client)
    cat_exp = _setup_expense_category(client, token)
    client.post(
        "/api/v1/budgets",
        json={
            "category_id": cat_exp["id"],
            "year": 2026,
            "month": 1,
            "limit_amount": "1000.00",
        },
        headers=_auth_header(token),
    )
    r = client.delete(f"/api/v1/categories/{cat_exp['id']}", headers=_auth_header(token))
    assert r.status_code == 204, r.text
    # orçamento deve ter sido excluído junto
    r = client.get("/api/v1/budgets/status?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json() == []
