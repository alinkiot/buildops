"""资质合规模块接口测试：CRUD、核验、到期扫描生成预警。"""


def test_qualification_list_seeded(client, admin_headers):
    resp = client.get("/api/qualifications", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 4
    # 列表包含距到期天数计算字段
    assert all("days_to_expire" in i for i in data["items"])


def test_qualification_crud(client, admin_headers):
    payload = {
        "name": "环保工程专业承包",
        "type": "专业承包",
        "level": "二级",
        "cert_no": "TEST-ENV-001",
        "valid_to": "2030-12-31",
        "status": "valid",
    }
    resp = client.post("/api/qualifications", json=payload, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    qid = resp.json()["data"]["id"]
    assert resp.json()["data"]["days_to_expire"] > 0

    resp = client.put(f"/api/qualifications/{qid}", json={"level": "一级"}, headers=admin_headers)
    assert resp.json()["data"]["level"] == "一级"

    assert client.get(f"/api/qualifications/{qid}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/qualifications/{qid}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/qualifications/{qid}", headers=admin_headers).status_code == 404


def test_qualification_verify_record(client, admin_headers):
    qid = client.get("/api/qualifications", headers=admin_headers).json()["data"]["items"][0]["id"]
    resp = client.post(
        f"/api/qualifications/{qid}/verify",
        json={"result": "verified", "method": "官网核验", "remark": "证书真实有效"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["result"] == "verified"

    records = client.get(f"/api/qualifications/{qid}/verify-records", headers=admin_headers)
    assert records.status_code == 200
    assert len(records.json()["data"]) >= 1

    # 资质核验状态被同步更新
    detail = client.get(f"/api/qualifications/{qid}", headers=admin_headers).json()["data"]
    assert detail["verify_status"] == "verified"


def test_scan_generates_alerts(client, admin_headers):
    before = client.get("/api/alerts", params={"source": "qualification"}, headers=admin_headers).json()["data"]["total"]

    resp = client.post("/api/qualifications/scan", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()["data"]
    # 种子里 1 个 25 天后到期(expiring) + 1 个已过期(expired)
    assert result["expiring"] >= 1
    assert result["expired"] >= 1
    assert result["alerts_created"] >= 2

    after = client.get("/api/alerts", params={"source": "qualification"}, headers=admin_headers).json()["data"]["total"]
    assert after >= before + 2

    # 再次扫描应去重，不再新增
    resp2 = client.post("/api/qualifications/scan", headers=admin_headers)
    assert resp2.json()["data"]["alerts_created"] == 0


def test_scan_updates_status(client, admin_headers):
    client.post("/api/qualifications/scan", headers=admin_headers)
    items = client.get("/api/qualifications", headers=admin_headers).json()["data"]["items"]
    statuses = {i["status"] for i in items}
    assert "expired" in statuses
    assert "expiring" in statuses
