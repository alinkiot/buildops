"""劳务法务模块测试：工人档案、工资、用工风险扫描、用工概览。"""


def test_workers_seeded(client, admin_headers):
    resp = client.get("/api/labor/workers", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 5


def test_labor_summary(client, admin_headers):
    resp = client.get("/api/labor/summary", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    assert d["total"] == 5
    assert d["onsite"] == 4  # 4 在场 + 1 离场
    # 在场中无合同：李大山、赵铁柱 = 2
    assert d["contract_missing"] == 2
    # 在场中保险缺失/过期：王师傅(过期)、赵铁柱(未参保) = 2
    assert d["insurance_missing"] == 2
    # 待发工资 7600 + 8800 = 16400
    assert float(d["unpaid_amount"]) == 16400.0


def test_labor_scan_generates_alerts(client, admin_headers):
    before = client.get("/api/alerts", params={"source": "labor"}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/labor/scan", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    # 3 名在场工人有风险（李大山、王师傅、赵铁柱）
    assert d["flagged"] == 3
    assert d["alerts_created"] == 3
    after = client.get("/api/alerts", params={"source": "labor"}, headers=admin_headers).json()["data"]["total"]
    assert after == before + 3
    # 去重
    again = client.post("/api/labor/scan", headers=admin_headers)
    assert again.json()["data"]["alerts_created"] == 0


def test_worker_risk_tag_set_after_scan(client, admin_headers):
    client.post("/api/labor/scan", headers=admin_headers)
    items = client.get("/api/labor/workers", params={"page_size": 50}, headers=admin_headers).json()["data"]["items"]
    zhao = next(w for w in items if w["name"] == "赵铁柱")
    assert zhao["risk_tag"] and "无劳动合同" in zhao["risk_tag"] and "工伤保险" in zhao["risk_tag"]
    # 离场工人不应有风险
    sun = next(w for w in items if w["name"] == "孙离场")
    assert not sun["risk_tag"]


def test_worker_crud_and_payroll(client, admin_headers):
    w = client.post("/api/labor/workers", json={
        "name": "测试工人", "team": "测试班", "craft": "电工", "status": "onsite", "contract_signed": True,
    }, headers=admin_headers).json()["data"]
    wid = w["id"]
    upd = client.put(f"/api/labor/workers/{wid}", json={"status": "left"}, headers=admin_headers)
    assert upd.json()["data"]["status"] == "left"

    pr = client.post(f"/api/labor/workers/{wid}/payroll", json={"period": "2026-06", "amount": "8000", "paid": True}, headers=admin_headers)
    assert pr.status_code == 200, pr.text
    logs = client.get(f"/api/labor/workers/{wid}/payroll", headers=admin_headers)
    assert len(logs.json()["data"]) == 1
    assert client.delete(f"/api/labor/workers/{wid}", headers=admin_headers).status_code == 200


def test_dashboard_includes_labor_source(client, admin_headers):
    client.post("/api/labor/scan", headers=admin_headers)
    resp = client.get("/api/dashboard", headers=admin_headers)
    sources = [s["name"] for s in resp.json()["data"]["alert_by_source"]]
    assert "劳务" in sources
