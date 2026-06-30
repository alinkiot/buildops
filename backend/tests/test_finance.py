"""财税账本模块测试：流水、利润表、无票风险扫描、税额联动。"""


def _project_id(client, headers, code="PRJ-2024-001"):
    items = client.get("/api/projects", params={"page_size": 50}, headers=headers).json()["data"]["items"]
    for it in items:
        if it["code"] == code:
            return it["id"]
    return items[0]["id"]


def test_finance_records_seeded(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.get("/api/finance", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 5


def test_profit_statement(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.get("/api/finance/profit", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    # 收入 50M+32M=82M，支出 30M+15M+8M=53M
    assert float(d["total_income"]) == 82000000.0
    assert float(d["total_expense"]) == 53000000.0
    assert float(d["gross_profit"]) == 29000000.0
    # 税额 4.5M+2.88M+3.9M+1.35M = 12.63M，净利 = 82-53-12.63 = 16.37M
    assert float(d["total_tax"]) == 12630000.0
    assert float(d["net_profit"]) == 16370000.0
    # 无票支出 8M / 53M ≈ 15.1%
    assert d["no_invoice_ratio"] > 10


def test_create_record_auto_tax(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.post("/api/finance", json={
        "project_id": pid, "direction": "income", "category": "尾款",
        "amount": "1000000", "tax_rate": "0.09",
    }, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    # 未传税额，自动按 amount*tax_rate=90000
    assert float(resp.json()["data"]["tax_amount"]) == 90000.0


def test_no_invoice_expense_tagged(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.post("/api/finance", json={
        "project_id": pid, "direction": "expense", "category": "现金采购",
        "amount": "5000", "has_invoice": False,
    }, headers=admin_headers)
    assert resp.json()["data"]["risk_tag"] == "无票"


def test_finance_scan_generates_alert(client, admin_headers):
    pid = _project_id(client, admin_headers)
    before = client.get("/api/alerts", params={"source": "finance", "project_id": pid}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/finance/scan", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    assert d["no_invoice_ratio"] > 10
    assert d["alerts_created"] == 1
    after = client.get("/api/alerts", params={"source": "finance", "project_id": pid}, headers=admin_headers).json()["data"]["total"]
    assert after == before + 1
    # 去重：再次扫描不新增
    again = client.post("/api/finance/scan", params={"project_id": pid}, headers=admin_headers)
    assert again.json()["data"]["alerts_created"] == 0


def test_finance_requires_project_id(client, admin_headers):
    assert client.get("/api/finance", headers=admin_headers).status_code == 422


def test_finance_filter_by_direction(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.get("/api/finance", params={"project_id": pid, "direction": "income"}, headers=admin_headers)
    assert resp.status_code == 200
    assert all(i["direction"] == "income" for i in resp.json()["data"]["items"])
