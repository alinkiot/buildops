"""三项增强测试：驾驶舱招投标/劳务指标、数据范围(项目授权)、第三方集成。"""


# ---------- ① 驾驶舱模块概览扩展 ----------
def test_dashboard_modules_bid_labor(client, admin_headers):
    m = client.get("/api/dashboard", headers=admin_headers).json()["data"]["modules"]
    assert "bid" in m and "labor" in m
    assert m["bid"]["total"] == 5
    assert m["bid"]["win_rate"] == 50.0
    assert m["labor"]["onsite"] == 4
    assert m["labor"]["contract_missing"] == 2


# ---------- ② 数据范围（按项目授权） ----------
def test_admin_sees_all_projects(client, admin_headers):
    total = client.get("/api/projects", params={"page_size": 50}, headers=admin_headers).json()["data"]["total"]
    assert total >= 3  # admin 超管，全部可见（含测试新建项目）


def test_pm_sees_only_authorized_projects(client, pm_headers):
    data = client.get("/api/projects", params={"page_size": 50}, headers=pm_headers).json()["data"]
    codes = {i["code"] for i in data["items"]}
    # pm 仅授权 管廊(PRJ-2024-001) 与 学校(PRJ-2024-002)，不含国防(PRJ-2023-018)
    assert "PRJ-2024-001" in codes
    assert "PRJ-2024-002" in codes
    assert "PRJ-2023-018" not in codes


def test_pm_cross_project_access_blocked(client, pm_headers, admin_headers):
    # 找到未授权给 pm 的国防项目 id
    items = client.get("/api/projects", params={"page_size": 50}, headers=admin_headers).json()["data"]["items"]
    guofang = next(i for i in items if i["code"] == "PRJ-2023-018")
    # pm 直接访问该项目详情应被拦截
    resp = client.get(f"/api/projects/{guofang['id']}", headers=pm_headers)
    assert resp.status_code == 403
    # pm 访问该项目的成本汇总也应被拦截
    resp2 = client.get("/api/costs/summary", params={"project_id": guofang["id"]}, headers=pm_headers)
    assert resp2.status_code == 403


def test_set_user_project_authorization(client, admin_headers):
    # 取 pm 用户与一个项目，演示授权接口
    users = client.get("/api/system/users", params={"page_size": 50}, headers=admin_headers).json()["data"]["items"]
    pm = next(u for u in users if u["username"] == "pm")
    projects = client.get("/api/projects", params={"page_size": 50}, headers=admin_headers).json()["data"]["items"]
    pid = projects[0]["id"]
    resp = client.put(f"/api/system/users/{pm['id']}/projects", json={"project_ids": [pid]}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["data"]) == 1
    # 恢复授权（避免影响其他用例）：授权管廊+学校
    codes = {p["code"]: p["id"] for p in projects}
    client.put(f"/api/system/users/{pm['id']}/projects",
               json={"project_ids": [codes["PRJ-2024-001"], codes["PRJ-2024-002"]]}, headers=admin_headers)


# ---------- ③ 第三方集成 ----------
def test_integration_providers_default_mock(client, admin_headers):
    resp = client.get("/api/integrations/providers", headers=admin_headers)
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["sms"] == "mock" and d["esign"] == "mock" and d["ocr"] == "mock"


def test_send_sms_mock_and_logged(client, admin_headers):
    before = client.get("/api/integrations/logs", params={"channel": "sms"}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/integrations/sms", json={"to": "13800000000", "content": "您的债权已逾期，请及时回款。"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "sent"
    assert resp.json()["data"]["message_id"].startswith("SMS-")
    after = client.get("/api/integrations/logs", params={"channel": "sms"}, headers=admin_headers).json()["data"]["total"]
    assert after == before + 1


def test_initiate_esign_mock(client, admin_headers):
    resp = client.post("/api/integrations/esign", json={"doc_name": "施工合同", "signers": ["甲方", "乙方"]}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    assert d["status"] == "signing"
    assert d["flow_id"].startswith("ESIGN-")
    assert "sign_url" in d


def test_ocr_recognize_mock(client, admin_headers):
    import io
    files = {"file": ("invoice.png", io.BytesIO(b"fakeimg"), "image/png")}
    resp = client.post("/api/integrations/ocr", files=files, data={"doc_type": "invoice"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    assert d["doc_type"] == "invoice"
    assert "金额" in d["fields"]


def test_integration_permission_denied_for_pm(client, pm_headers):
    resp = client.post("/api/integrations/sms", json={"to": "13800000000", "content": "x"}, headers=pm_headers)
    assert resp.status_code == 403
