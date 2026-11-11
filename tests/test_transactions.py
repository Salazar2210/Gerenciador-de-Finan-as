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


def _setup_user_with_account_and_categories(client, token):
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


def test_create_transaction_success(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    r = client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "1500.00",
            "date": "2026-01-10",
            "description": "Pagamento",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["amount"] == "1500.00"
    assert data["type"] == "INCOME"


def test_transaction_type_must_match_category(client, db):
    token = _register_and_login(client)
    cat_inc, cat_exp = _setup_user_with_account_and_categories(client, token)
    # type INCOME com categoria EXPENSE
    r = client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_exp["id"],
            "type": "INCOME",
            "amount": "100.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 422, r.text
    # type EXPENSE com categoria INCOME
    r = client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "EXPENSE",
            "amount": "100.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 422, r.text


def test_transaction_account_of_another_user_404(client, db):
    token_a = _register_and_login(client, email="a@exemplo.com")
    token_b = _register_and_login(client, email="b@exemplo.com")
    _setup_user_with_account_and_categories(client, token_a)
    _setup_user_with_account_and_categories(client, token_b)
    r = client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": 1,
            "type": "EXPENSE",
            "amount": "100.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token_b),
    )
    assert r.status_code == 404, r.text


def test_transaction_amount_must_be_positive(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    r = client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "0",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    assert r.status_code == 422, r.text


def test_list_transactions_pagination_and_total(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    for i in range(5):
        client.post(
            "/api/v1/transactions",
            json={
                "account_id": 1,
                "category_id": cat_inc["id"],
                "type": "INCOME",
                "amount": "100.00",
                "date": f"2026-01-1{i+1}",
            },
            headers=_auth_header(token),
        )
    r = client.get("/api/v1/transactions?limit=2&offset=0", headers=_auth_header(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2


def test_list_transactions_ordering(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "100.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "200.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/transactions", headers=_auth_header(token))
    assert r.status_code == 200
    items = r.json()["items"]
    # mesma data: id decrescente
    assert items[0]["amount"] == "200.00"
    assert items[1]["amount"] == "100.00"


def test_list_transactions_filters(client, db):
    token = _register_and_login(client)
    cat_inc, cat_exp = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "1000.00",
            "date": "2026-01-10",
            "description": "Salário janeiro",
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
            "date": "2026-02-15",
            "description": "Mercado",
        },
        headers=_auth_header(token),
    )
    r = client.get(
        "/api/v1/transactions?type=INCOME&min_amount=500&search=salário",
        headers=_auth_header(token),
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_get_transaction_by_id(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.get("/api/v1/transactions/1", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_transaction_404_other_user(client, db):
    token_a = _register_and_login(client, email="a@exemplo.com")
    token_b = _register_and_login(client, email="b@exemplo.com")
    _setup_user_with_account_and_categories(client, token_a)
    _setup_user_with_account_and_categories(client, token_b)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": 1,
            "type": "EXPENSE",
            "amount": "100.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token_a),
    )
    r = client.get("/api/v1/transactions/1", headers=_auth_header(token_b))
    assert r.status_code == 404, r.text


def test_update_transaction(client, db):
    token = _register_and_login(client)
    cat_inc, cat_exp = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.patch(
        "/api/v1/transactions/1",
        json={"amount": "700.00", "description": "Atualizado"},
        headers=_auth_header(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == "700.00"
    assert r.json()["description"] == "Atualizado"


def test_update_transaction_revalidates_type_category(client, db):
    token = _register_and_login(client)
    cat_inc, cat_exp = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.patch(
        "/api/v1/transactions/1",
        json={"category_id": cat_exp["id"]},
        headers=_auth_header(token),
    )
    assert r.status_code == 422, r.text


def test_delete_transaction(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.delete("/api/v1/transactions/1", headers=_auth_header(token))
    assert r.status_code == 204, r.text


def test_delete_account_with_transactions_409(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.delete("/api/v1/accounts/1", headers=_auth_header(token))
    assert r.status_code == 409, r.text


def test_delete_category_with_transactions_409(client, db):
    token = _register_and_login(client)
    cat_inc, _ = _setup_user_with_account_and_categories(client, token)
    client.post(
        "/api/v1/transactions",
        json={
            "account_id": 1,
            "category_id": cat_inc["id"],
            "type": "INCOME",
            "amount": "500.00",
            "date": "2026-01-10",
        },
        headers=_auth_header(token),
    )
    r = client.delete(f"/api/v1/categories/{cat_inc['id']}", headers=_auth_header(token))
    assert r.status_code == 409, r.text
