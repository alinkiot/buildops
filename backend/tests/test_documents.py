"""工程资料模块测试：模板、清单、上传、审核、缺项扫描、完整度、组卷。"""
import io


def _managed_project_id(client, headers):
    """取种子里挂了资料条目的管廊项目 id。"""
    items = client.get("/api/projects", params={"page_size": 50}, headers=headers).json()["data"]["items"]
    for it in items:
        if it["code"] == "PRJ-2024-001":
            return it["id"]
    return items[0]["id"]


def test_templates_seeded(client, admin_headers):
    resp = client.get("/api/documents/templates", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 5


def test_doc_items_listed_for_project(client, admin_headers):
    pid = _managed_project_id(client, admin_headers)
    resp = client.get("/api/documents", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 5


def test_list_requires_project_id(client, admin_headers):
    assert client.get("/api/documents", headers=admin_headers).status_code == 422


def test_apply_template_creates_items(client, admin_headers):
    # 新建一个空项目，应用模板
    p = client.post("/api/projects", json={"code": "PRJ-DOC-1", "name": "资料测试项目", "contract_amount": "1"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    resp = client.post("/api/documents/apply-template", json={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["created"] >= 5
    # 重复应用应去重
    resp2 = client.post("/api/documents/apply-template", json={"project_id": pid}, headers=admin_headers)
    assert resp2.json()["data"]["created"] == 0
    # 列表可见
    total = client.get("/api/documents", params={"project_id": pid}, headers=admin_headers).json()["data"]["total"]
    assert total >= 5


def test_upload_and_review_flow(client, admin_headers):
    p = client.post("/api/projects", json={"code": "PRJ-DOC-2", "name": "上传审核项目", "contract_amount": "1"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    client.post("/api/documents/apply-template", json={"project_id": pid}, headers=admin_headers)
    item = client.get("/api/documents", params={"project_id": pid}, headers=admin_headers).json()["data"]["items"][0]
    iid = item["id"]

    # 上传 -> 待审核
    files = {"file": ("doc.pdf", io.BytesIO(b"document content"), "application/pdf")}
    up = client.post(f"/api/documents/{iid}/upload", files=files, headers=admin_headers)
    assert up.status_code == 200, up.text
    assert up.json()["data"]["status"] == "pending_review"
    assert up.json()["data"]["version"] == 1

    # 审核退回
    rev = client.post(f"/api/documents/{iid}/review", json={"approved": False, "review_remark": "缺签字"}, headers=admin_headers)
    assert rev.json()["data"]["status"] == "returned"

    # 重新上传 -> 审核通过
    client.post(f"/api/documents/{iid}/upload", files={"file": ("doc2.pdf", io.BytesIO(b"v2"), "application/pdf")}, headers=admin_headers)
    rev2 = client.post(f"/api/documents/{iid}/review", json={"approved": True}, headers=admin_headers)
    assert rev2.json()["data"]["status"] == "approved"
    assert rev2.json()["data"]["version"] == 2


def test_scan_missing_generates_alert(client, admin_headers):
    pid = _managed_project_id(client, admin_headers)
    before = client.get("/api/alerts", params={"source": "document", "project_id": pid}, headers=admin_headers).json()["data"]["total"]
    resp = client.post("/api/documents/scan", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    # 种子里"隐蔽工程验收记录"逾期未上传 -> 缺项
    assert resp.json()["data"]["missing"] >= 1
    assert resp.json()["data"]["alerts_created"] >= 1
    after = client.get("/api/alerts", params={"source": "document", "project_id": pid}, headers=admin_headers).json()["data"]["total"]
    assert after >= before + 1
    # 去重
    again = client.post("/api/documents/scan", params={"project_id": pid}, headers=admin_headers)
    assert again.json()["data"]["alerts_created"] == 0


def test_completeness(client, admin_headers):
    pid = _managed_project_id(client, admin_headers)
    resp = client.get("/api/documents/completeness", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] >= 5
    assert 0 <= data["completeness"] <= 100


def test_archive(client, admin_headers):
    p = client.post("/api/projects", json={"code": "PRJ-DOC-3", "name": "组卷项目", "contract_amount": "1"}, headers=admin_headers)
    pid = p.json()["data"]["id"]
    client.post("/api/documents/apply-template", json={"project_id": pid}, headers=admin_headers)
    item = client.get("/api/documents", params={"project_id": pid}, headers=admin_headers).json()["data"]["items"][0]
    iid = item["id"]
    client.post(f"/api/documents/{iid}/upload", files={"file": ("a.pdf", io.BytesIO(b"x"), "application/pdf")}, headers=admin_headers)
    client.post(f"/api/documents/{iid}/review", json={"approved": True}, headers=admin_headers)

    resp = client.post("/api/documents/archive", params={"project_id": pid}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["archived"] >= 1
    assert len(resp.json()["data"]["manifest"]) >= 1
