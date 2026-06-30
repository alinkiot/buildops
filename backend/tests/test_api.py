"""核心接口测试：认证、权限、项目、文件、预警、驾驶舱。"""
import io


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "up"


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert resp.status_code == 401


def test_me_returns_permissions(client, admin_headers):
    resp = client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "admin"
    assert data["is_superadmin"] is True
    assert "*" in data["permissions"]


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_dashboard_overview(client, admin_headers):
    resp = client.get("/api/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    ov = resp.json()["data"]["overview"]
    assert ov["project_count"] == 3
    # 合同额 = 1.28亿 + 5600万 + 3200万
    assert float(ov["contract_amount"]) == 216000000.0
    assert ov["alert_count"] == 4
    assert ov["pending_alert_count"] >= 1


def test_project_crud(client, admin_headers):
    # 列表
    resp = client.get("/api/projects", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 3

    # 新增
    payload = {
        "code": "PRJ-TEST-100",
        "name": "测试道路工程",
        "type": "市政",
        "contract_amount": "10000000",
        "status": "ongoing",
    }
    resp = client.post("/api/projects", json=payload, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    pid = resp.json()["data"]["id"]

    # 编码重复
    assert client.post("/api/projects", json=payload, headers=admin_headers).status_code == 400

    # 更新
    resp = client.put(f"/api/projects/{pid}", json={"name": "测试道路工程二期"}, headers=admin_headers)
    assert resp.json()["data"]["name"] == "测试道路工程二期"

    # 详情
    assert client.get(f"/api/projects/{pid}", headers=admin_headers).status_code == 200

    # 删除
    assert client.delete(f"/api/projects/{pid}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/projects/{pid}", headers=admin_headers).status_code == 404


def test_project_filter_by_status(client, admin_headers):
    resp = client.get("/api/projects", params={"status": "ongoing"}, headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all(i["status"] == "ongoing" for i in items)


def test_file_upload_and_download(client, admin_headers):
    files = {"file": ("test.txt", io.BytesIO(b"hello construction"), "text/plain")}
    resp = client.post(
        "/api/files/upload",
        files=files,
        data={"business_type": "测试", "secret_level": "internal"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    fid = resp.json()["data"]["id"]
    assert resp.json()["data"]["size"] == len(b"hello construction")

    dl = client.get(f"/api/files/{fid}/download", headers=admin_headers)
    assert dl.status_code == 200
    assert dl.content == b"hello construction"


def test_alert_handle_flow(client, admin_headers):
    resp = client.get("/api/alerts", params={"status": "pending"}, headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    aid = items[0]["id"]

    resp = client.post(
        f"/api/alerts/{aid}/handle",
        json={"status": "closed", "handle_remark": "已处理完毕"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "closed"
    assert resp.json()["data"]["closed_at"] is not None


def test_permission_denied_for_pm_on_user_management(client, pm_headers):
    # 项目负责人没有 system:user:manage 权限
    resp = client.post(
        "/api/system/users",
        json={"username": "x1", "password": "123456", "name": "X"},
        headers=pm_headers,
    )
    assert resp.status_code == 403


def test_pm_can_create_project(client, pm_headers):
    resp = client.post(
        "/api/projects",
        json={"code": "PRJ-PM-1", "name": "PM建的项目", "contract_amount": "1"},
        headers=pm_headers,
    )
    assert resp.status_code == 200, resp.text


def test_audit_log_recorded(client, admin_headers):
    resp = client.get("/api/system/audit-logs", params={"action": "login"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


def test_create_user_and_login(client, admin_headers):
    # 取一个角色
    roles = client.get("/api/system/roles", headers=admin_headers).json()["data"]
    role_id = roles[0]["id"]
    resp = client.post(
        "/api/system/users",
        json={"username": "newbie", "password": "pass1234", "name": "新人", "role_ids": [role_id]},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    # 新用户登录
    login = client.post("/api/auth/login", json={"username": "newbie", "password": "pass1234"})
    assert login.status_code == 200
