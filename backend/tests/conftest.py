"""测试夹具：使用独立临时数据库并注入种子数据。"""
import os
import tempfile

import pytest

# 在导入 app 前指定独立测试库
_TMP_DB = os.path.join(tempfile.gettempdir(), "construction_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["APP_DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["APP_UPLOAD_DIR"] = os.path.join(tempfile.gettempdir(), "construction_uploads")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed_db():
    seed()
    yield
    if os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)


@pytest.fixture()
def client():
    return TestClient(app)


def _login(client, username, password):
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client):
    return _login(client, "admin", "admin123")


@pytest.fixture()
def pm_headers(client):
    return _login(client, "pm", "pm123")
