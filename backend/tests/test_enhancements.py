"""系统增强测试：驾驶舱模块概览、CSV 导出、文件在线预览。"""
import io


def test_dashboard_modules_overview(client, admin_headers):
    resp = client.get("/api/dashboard", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    m = resp.json()["data"]["modules"]
    assert m is not None
    # 资质健康度
    assert m["qualification"]["total"] == 4
    assert 0 <= m["qualification"]["health_score"] <= 100
    # 资料完整度
    assert m["document"]["required_total"] >= 1
    assert 0 <= m["document"]["completeness"] <= 100
    # 成本（含其他用例新增预算，至少包含种子 79M）
    assert float(m["cost"]["total_budget"]) >= 79000000.0
    assert m["cost"]["over_budget_projects"] >= 1
    # 财税利润
    assert float(m["finance"]["total_income"]) >= 82000000.0
    assert m["finance"]["no_invoice_ratio"] > 0
    # 回款分级与最差甲方
    assert float(m["receivable"]["total_outstanding"]) > 0
    assert m["receivable"]["worst_client_level"] in ("A", "B", "C", "D", None)


def test_export_projects_csv(client, admin_headers):
    resp = client.get("/api/export/projects", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    text = resp.content.decode("utf-8-sig")
    lines = [l for l in text.splitlines() if l.strip()]
    assert lines[0].startswith("项目编号")
    assert len(lines) >= 4  # 表头 + 至少3个种子项目


def test_export_receivables_csv(client, admin_headers):
    resp = client.get("/api/export/receivables", headers=admin_headers)
    assert resp.status_code == 200
    text = resp.content.decode("utf-8-sig")
    assert "甲方" in text.splitlines()[0]


def test_export_alerts_csv_filtered(client, admin_headers):
    resp = client.get("/api/export/alerts", params={"source": "qualification"}, headers=admin_headers)
    assert resp.status_code == 200
    assert "预警标题" in resp.content.decode("utf-8-sig").splitlines()[0]


def test_file_preview_image(client, admin_headers):
    # 上传一个 png（伪内容，仅校验 inline 返回）
    files = {"file": ("pic.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfakepng"), "image/png")}
    up = client.post("/api/files/upload", files=files, data={"secret_level": "internal"}, headers=admin_headers)
    fid = up.json()["data"]["id"]
    resp = client.get(f"/api/files/{fid}/preview", headers=admin_headers)
    assert resp.status_code == 200
    assert "inline" in resp.headers.get("content-disposition", "")


def test_file_preview_unsupported_type(client, admin_headers):
    files = {"file": ("a.zip", io.BytesIO(b"PK\x03\x04zip"), "application/zip")}
    up = client.post("/api/files/upload", files=files, data={"secret_level": "internal"}, headers=admin_headers)
    fid = up.json()["data"]["id"]
    resp = client.get(f"/api/files/{fid}/preview", headers=admin_headers)
    assert resp.status_code == 415
