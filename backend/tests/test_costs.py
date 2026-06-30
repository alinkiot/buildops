"""成本管理模块测试：预算、支出超预算检测、审批、偏差汇总、成本回写。"""


def _project_id(client, headers, code="PRJ-2024-001"):
    items = client.get("/api/projects", params={"page_size": 50}, headers=headers).json()["data"]["items"]
    for it in items:
        if it["code"] == code:
            return it["id"]
    return items[0]["id"]


def test_budgets_seeded(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.get("/api/costs/budgets", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 4


def test_cost_summary_and_deviation(client, admin_headers):
    pid = _project_id(client, admin_headers)
    resp = client.get("/api/costs/summary", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert float(data["total_budget"]) == 79000000.0
    # 已计入支出 35+16+5.5+12+0.5+1 = 70.0M
    assert float(data["total_actual"]) == 70000000.0
    assert data["pending_approval"] >= 1
    assert float(data["no_invoice_amount"]) == 500000.0
    # 机械费超预算（5.5M+1M=6.5M > 6M）
    machine = next(d for d in data["deviations"] if d["category"] == "机械费")
    assert machine["over_budget"] is True


def test_expense_within_budget_registered(client, admin_headers):
    p = client.post("/api/projects", json={"code": "PRJ-COST-1", "name": "成本测试", "contract_amount": "1"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    client.post("/api/costs/budgets", json={"project_id": pid, "category": "材料费", "budget_amount": "1000000"}, headers=admin_headers)
    resp = client.post("/api/costs/expenses", json={"project_id": pid, "category": "材料费", "type": "material", "amount": "300000"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "registered"
    assert resp.json()["data"]["over_budget"] is False


def test_expense_over_budget_triggers_approval_and_alert(client, admin_headers):
    p = client.post("/api/projects", json={"code": "PRJ-COST-2", "name": "超预算测试", "contract_amount": "1"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    client.post("/api/costs/budgets", json={"project_id": pid, "category": "机械费", "budget_amount": "100000"}, headers=admin_headers)

    before = client.get("/api/alerts", params={"source": "cost", "project_id": pid}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/costs/expenses", json={"project_id": pid, "category": "机械费", "type": "machine", "amount": "150000"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    eid = resp.json()["data"]["id"]
    assert resp.json()["data"]["status"] == "pending_approval"
    assert resp.json()["data"]["over_budget"] is True

    after = client.get("/api/alerts", params={"source": "cost", "project_id": pid}, headers=admin_headers).json()["data"]["total"]
    assert after == before + 1

    # 审批通过 -> 已付款
    appr = client.post(f"/api/costs/expenses/{eid}/approve", json={"approved": True, "approve_remark": "同意"}, headers=admin_headers)
    assert appr.status_code == 200
    assert appr.json()["data"]["status"] == "paid"


def test_cost_writes_back_to_project(client, admin_headers):
    p = client.post("/api/projects", json={"code": "PRJ-COST-3", "name": "成本回写", "contract_amount": "5000000"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    client.post("/api/costs/expenses", json={"project_id": pid, "type": "other", "amount": "1234567"}, headers=admin_headers)
    proj = client.get(f"/api/projects/{pid}", headers=admin_headers).json()["data"]
    assert float(proj["cost_amount"]) == 1234567.0


def test_pm_cannot_approve(client, pm_headers, admin_headers):
    # pm 有 cost:manage 但无 cost:approve
    p = client.post("/api/projects", json={"code": "PRJ-COST-4", "name": "审批权限", "contract_amount": "1"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    # 先把该项目授权给 pm（数据范围），使其可登记支出
    users = client.get("/api/system/users", params={"page_size": 50}, headers=admin_headers).json()["data"]["items"]
    pm_user = next(u for u in users if u["username"] == "pm")
    cur = client.get(f"/api/system/users/{pm_user['id']}/projects", headers=admin_headers).json()["data"]
    client.put(f"/api/system/users/{pm_user['id']}/projects",
               json={"project_ids": [x["id"] for x in cur] + [pid]}, headers=admin_headers)
    client.post("/api/costs/budgets", json={"project_id": pid, "category": "材料费", "budget_amount": "100"}, headers=admin_headers)
    exp = client.post("/api/costs/expenses", json={"project_id": pid, "category": "材料费", "type": "material", "amount": "200"}, headers=pm_headers)
    eid = exp.json()["data"]["id"]
    resp = client.post(f"/api/costs/expenses/{eid}/approve", json={"approved": True}, headers=pm_headers)
    assert resp.status_code == 403
    # 还原 pm 授权，避免影响其他用例顺序
    client.put(f"/api/system/users/{pm_user['id']}/projects",
               json={"project_ids": [x["id"] for x in cur]}, headers=admin_headers)
