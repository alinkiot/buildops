"""招投标模块测试：台账、资质准入校验(R-002)、保证金扫描、投标看板与中标率。"""


def _find(client, headers, kw):
    items = client.get("/api/tenders", params={"page_size": 50}, headers=headers).json()["data"]["items"]
    return next(i for i in items if kw in i["name"])


def test_tenders_seeded(client, admin_headers):
    resp = client.get("/api/tenders", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 5


def test_board_and_win_rate(client, admin_headers):
    resp = client.get("/api/tenders/board", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    # 已中标1 未中标1 -> 中标率 50%
    assert d["won"] == 1
    assert d["win_rate"] == 50.0
    # 未退保证金：50万+80万+30万 = 160万
    assert float(d["deposit_outstanding"]) == 1600000.0
    assert d["deposit_overdue"] >= 1


def test_evaluate_can_bid(client, admin_headers):
    # 产业园厂房：要求 建筑工程施工总承包 + 安全生产许可证（均为有效资质）-> 可投
    t = _find(client, admin_headers, "产业园厂房")
    resp = client.post(f"/api/tenders/{t['id']}/evaluate", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["can_bid"] is True
    assert resp.json()["data"]["status"] == "can_bid"


def test_evaluate_cannot_bid_with_expired_qual_creates_alert(client, admin_headers):
    # 经开区道路：要求 市政公用工程施工总承包（种子里该资质已过期）-> 不可投 + 预警
    t = _find(client, admin_headers, "经开区道路")
    before = client.get("/api/alerts", params={"source": "bid"}, headers=admin_headers).json()["data"]["total"]
    resp = client.post(f"/api/tenders/{t['id']}/evaluate", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    assert d["can_bid"] is False
    assert d["status"] == "cannot_bid"
    assert len(d["reasons"]) >= 1
    after = client.get("/api/alerts", params={"source": "bid"}, headers=admin_headers).json()["data"]["total"]
    assert after == before + 1


def test_scan_deposit_generates_alert(client, admin_headers):
    before = client.get("/api/alerts", params={"source": "bid"}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/tenders/scan-deposit", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["overdue"] >= 1
    assert resp.json()["data"]["alerts_created"] >= 1
    after = client.get("/api/alerts", params={"source": "bid"}, headers=admin_headers).json()["data"]["total"]
    assert after >= before + 1
    # 去重
    again = client.post("/api/tenders/scan-deposit", headers=admin_headers)
    assert again.json()["data"]["alerts_created"] == 0


def test_tender_crud(client, admin_headers):
    resp = client.post("/api/tenders", json={
        "name": "测试桥梁工程招标", "project_type": "公路", "region": "北京",
        "qualification_req": "建筑工程施工总承包", "deposit_amount": "100000",
    }, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    tid = resp.json()["data"]["id"]
    upd = client.put(f"/api/tenders/{tid}", json={"status": "bidded"}, headers=admin_headers)
    assert upd.json()["data"]["status"] == "bidded"
    assert client.delete(f"/api/tenders/{tid}", headers=admin_headers).status_code == 200


def test_dashboard_includes_bid_alerts(client, admin_headers):
    # 触发一次评估/扫描后，驾驶舱预警来源应包含招投标
    client.post("/api/tenders/scan-deposit", headers=admin_headers)
    resp = client.get("/api/dashboard", headers=admin_headers)
    sources = [s["name"] for s in resp.json()["data"]["alert_by_source"]]
    assert "招投标" in sources
