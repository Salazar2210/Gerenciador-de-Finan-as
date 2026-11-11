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


def _setup(client, token):
    client.post(
        "/api/v1/accounts",
        json={"name": "Carteira", "initial_balance": "0.00"},
        headers=_auth_header(token),
    )
    cat_inc = client.post(
        "/api/v1/categories",
        json={"name": "Salário", "type": "INCOME"},
        headers=_auth_header(token),
    ).json()
    cat_exp = client.post(
        "/api/v1/categories",
        json={"name": "Mercado", "type": "EXPENSE"},
        headers=_auth_header(token),
    ).json()
    return cat_inc, cat_exp


def _tx(client, token, account_id, category_id, type_, amount, date, description=None):
    payload = {
        "account_id": account_id,
        "category_id": category_id,
        "type": type_,
        "amount": amount,
        "date": date,
    }
    if description:
        payload["description"] = description
    return client.post("/api/v1/transactions", json=payload, headers=_auth_header(token))


def test_monthly_summary(client, db):
    token = _register_and_login(client)
    cat_inc, cat_exp = _setup(client, token)
    _tx(client, token, 1, cat_inc["id"], "INCOME", "2000.00", "2026-01-05", "Salário")
    _tx(client, token, 1, cat_inc["id"], "INCOME", "500.00", "2026-01-20", "Freela")
    _tx(client, token, 1, cat_exp["id"], "EXPENSE", "300.00", "2026-01-10", "Mercado")
    _tx(client, token, 1, cat_exp["id"], "EXPENSE", "200.00", "2026-02-01", "Mercado fevereiro")
    r = client.get("/api/v1/reports/monthly-summary?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["year"] == 2026
    assert data["month"] == 1
    assert data["total_income"] == "2500.00"
    assert data["total_expense"] == "300.00"
    assert data["balance"] == "2200.00"


def test_monthly_summary_boundaries_day1_and_last_day(client, db):
    token = _register_and_login(client)
    cat_exp = _setup(client, token)[1]
    # último dia de janeiro
    _tx(client, token, 1, cat_exp["id"], "EXPENSE", "100.00", "2026-01-31", "Último dia")
    # primeiro dia de fevereiro (não deve entrar em janeiro)
    _tx(
        client, token, 1, cat_exp["id"], "EXPENSE", "500.00", "2026-02-01", "Primeiro dia fevereiro"
    )
    r = client.get("/api/v1/reports/monthly-summary?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["total_expense"] == "100.00"


def test_by_category_expense(client, db):
    token = _register_and_login(client)
    cat_inc, cat_exp = _setup(client, token)
    _tx(client, token, 1, cat_exp["id"], "EXPENSE", "300.00", "2026-01-10", "Mercado A")
    _tx(client, token, 1, cat_exp["id"], "EXPENSE", "100.00", "2026-01-15", "Mercado B")
    r = client.get(
        "/api/v1/reports/by-category?year=2026&month=1&type=EXPENSE", headers=_auth_header(token)
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["category_id"] == cat_exp["id"]
    assert data[0]["total"] == "400.00"
    assert data[0]["percentage"] == "100.00"


def test_by_category_default_type_expense(client, db):
    token = _register_and_login(client)
    cat_exp = _setup(client, token)[1]
    _tx(client, token, 1, cat_exp["id"], "EXPENSE", "100.00", "2026-01-10")
    r = client.get("/api/v1/reports/by-category?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_by_category_empty(client, db):
    token = _register_and_login(client)
    r = client.get("/api/v1/reports/by-category?year=2026&month=1", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json() == []


def test_monthly_evolution_default_6(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup(client, token)
    _tx(client, token, 1, cat_inc["id"], "INCOME", "1000.00", "2026-01-10")
    r = client.get("/api/v1/reports/monthly-evolution", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 6
    # ordem antiga para recente
    assert data[0]["year"] <= data[-1]["year"]


def test_monthly_evolution_custom_months(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup(client, token)
    _tx(client, token, 1, cat_inc["id"], "INCOME", "1000.00", "2026-01-10")
    r = client.get("/api/v1/reports/monthly-evolution?months=3", headers=_auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_monthly_evolution_months_bounds(client, db):
    token = _register_and_login(client)
    r = client.get("/api/v1/reports/monthly-evolution?months=0", headers=_auth_header(token))
    assert r.status_code == 422, r.text
    r = client.get("/api/v1/reports/monthly-evolution?months=25", headers=_auth_header(token))
    assert r.status_code == 422, r.text


def test_monthly_evolution_empty_months_show_zero(client, db):
    token = _register_and_login(client)
    _setup(client, token)
    # sem transações
    r = client.get("/api/v1/reports/monthly-evolution?months=2", headers=_auth_header(token))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    for item in data:
        assert item["total_income"] == "0.00"
        assert item["total_expense"] == "0.00"
        assert item["balance"] == "0.00"
