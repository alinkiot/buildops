"""回款清欠模块测试：债权、日志、回款登记+财税同步、逾期分级扫描、汇总信用、文书。"""


def _list(client, headers, **params):
    return client.get("/api/receivables", params=params, headers=headers).json()["data"]


def test_receivables_seeded(client, admin_headers):
    data = _list(client, admin_headers)
    assert data["total"] == 4
    # 含计算字段
    assert all("outstanding" in i and "overdue_days" in i for i in data["items"])


def test_overdue_days_computed(client, admin_headers):
    items = _list(client, admin_headers)["items"]
    # 国防尾款逾期约 200 天
    legal = next(i for i in items if i["contract_no"] == "HT-2023-018")
    assert legal["overdue_days"] >= 180
    assert float(legal["outstanding"]) == 20000000.0


def test_scan_grades_and_alerts(client, admin_headers):
    before = client.get("/api/alerts", params={"source": "receivable"}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/receivables/scan", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    # 学校尾款逾期100天→呆滞；国防尾款逾期200天→坏账风险
    assert d["stagnant"] >= 1
    assert d["bad_debt_risk"] >= 1
    assert d["alerts_created"] >= 2
    after = client.get("/api/alerts", params={"source": "receivable"}, headers=admin_headers).json()["data"]["total"]
    assert after >= before + 2
    # 去重
    again = client.post("/api/receivables/scan", headers=admin_headers)
    assert again.json()["data"]["alerts_created"] == 0


def test_payment_syncs_finance(client, admin_headers):
    # 找学校尾款债权（有 project，可同步财税）
    items = _list(client, admin_headers)["items"]
    r = next(i for i in items if i["contract_no"] == "HT-2024-002")
    rid = r["id"]
    pid = r["project_id"]

    fin_before = client.get("/api/finance", params={"project_id": pid}, headers=admin_headers).json()["data"]["total"]
    resp = client.post(f"/api/receivables/{rid}/payment", json={"amount": "1000000", "sync_finance": True}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["data"]["received_amount"]) == 3000000.0  # 2M + 1M
    assert resp.json()["data"]["status"] == "partial"

    # 财税新增一条回款收入流水
    fin_after = client.get("/api/finance", params={"project_id": pid}, headers=admin_headers).json()["data"]["total"]
    assert fin_after == fin_before + 1

    # 催收日志生成回款记录
    logs = client.get(f"/api/receivables/{rid}/logs", headers=admin_headers).json()["data"]
    assert any(l["type"] == "payment" for l in logs)


def test_payment_settles_when_full(client, admin_headers):
    r = client.post("/api/receivables", json={"debt_type": "other", "amount": "5000"}, headers=admin_headers).json()["data"]
    resp = client.post(f"/api/receivables/{r['id']}/payment", json={"amount": "5000", "sync_finance": False}, headers=admin_headers)
    assert resp.json()["data"]["status"] == "settled"
    assert float(resp.json()["data"]["outstanding"]) == 0.0


def test_collection_log_add(client, admin_headers):
    rid = _list(client, admin_headers)["items"][0]["id"]
    resp = client.post(f"/api/receivables/{rid}/logs", json={"type": "visit", "content": "上门洽谈", "result": "承诺月底付款"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["type"] == "visit"
    assert resp.json()["data"]["operator_name"] is not None


def test_summary_and_credit(client, admin_headers):
    resp = client.get("/api/receivables/summary", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    assert float(d["total_amount"]) > 0
    assert len(d["tiers"]) == 3
    assert len(d["clients"]) >= 1
    # 每个甲方有信用分与等级
    for c in d["clients"]:
        assert 0 <= c["credit_score"] <= 100
        assert c["credit_level"] in ("A", "B", "C", "D")


def test_generate_letter(client, admin_headers):
    items = _list(client, admin_headers)["items"]
    r = next(i for i in items if i["contract_no"] == "HT-2023-018")
    resp = client.get(f"/api/receivables/{r['id']}/letter", params={"kind": "lawyer"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["title"] == "律师函"
    assert "应付未付款项" in data["content"]
    assert data["overdue_days"] >= 1


def test_pm_cannot_manage_receivable(client, pm_headers):
    # pm 无 receivable:manage 权限
    resp = client.post("/api/receivables", json={"debt_type": "other", "amount": "1"}, headers=pm_headers)
    assert resp.status_code == 403
