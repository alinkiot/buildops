"""FastAPI 应用入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alerts, auth, costs, dashboard, documents, exports, files, finance, integrations, labor, projects, qualifications, receivables, system, tenders
from app.core.config import settings
from app.db.session import Base, engine
from app.schemas.common import ok

# 首期开发用 create_all 建表；生产建议改用 Alembic 迁移
import app.models  # noqa: F401  确保模型注册
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.API_PREFIX
app.include_router(auth.router, prefix=api)
app.include_router(system.router, prefix=api)
app.include_router(projects.router, prefix=api)
app.include_router(qualifications.router, prefix=api)
app.include_router(documents.router, prefix=api)
app.include_router(costs.router, prefix=api)
app.include_router(finance.router, prefix=api)
app.include_router(receivables.router, prefix=api)
app.include_router(exports.router, prefix=api)
app.include_router(tenders.router, prefix=api)
app.include_router(labor.router, prefix=api)
app.include_router(integrations.router, prefix=api)
app.include_router(files.router, prefix=api)
app.include_router(alerts.router, prefix=api)
app.include_router(dashboard.router, prefix=api)


@app.get("/health")
def health():
    return ok({"status": "up", "name": settings.PROJECT_NAME})


# ---------------------------------------------------------------------------
# 生产部署：托管前端 SPA 静态资源
# 仅当存在打包产物（容器内 backend/static）时启用，不影响本地开发与测试。
# ---------------------------------------------------------------------------
from pathlib import Path  # noqa: E402

from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if (_STATIC_DIR / "index.html").is_file():
    _assets = _STATIC_DIR / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/", include_in_schema=False)
    def _spa_index():
        return FileResponse(str(_STATIC_DIR / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str):
        # 命中真实静态文件则返回，否则回退到 index.html 交给前端路由
        candidate = _STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_STATIC_DIR / "index.html"))
