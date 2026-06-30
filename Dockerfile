# syntax=docker/dockerfile:1

# ============================================================
# 施工企业全流程运营托管数字化系统 —— 单镜像多阶段构建
# 阶段一：构建前端 (React + Vite) -> 静态产物
# 阶段二：Python 运行镜像，由 FastAPI 托管前端静态资源 + 提供 /api
# ============================================================

# ---------- 阶段一：构建前端 ----------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# 优先拷贝依赖清单以利用层缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 拷贝源码并构建（tsc --noEmit && vite build）
COPY frontend/ ./
RUN npm run build


# ---------- 阶段二：后端运行镜像 ----------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 默认将数据库与上传文件放到可挂载的 /data 卷，保证容器重建后数据不丢失
    APP_DATABASE_URL=sqlite:////data/construction_mvp.db \
    APP_UPLOAD_DIR=/data/uploads

WORKDIR /app

# curl 供 HEALTHCHECK 使用
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（层缓存）
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# 后端源码
COPY backend/app ./app

# 前端构建产物 -> backend/static（main.py 会自动挂载）
COPY --from=frontend-builder /app/frontend/dist ./static

# 入口脚本
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data/uploads

# 以非 root 用户运行，并赋予 /data 写权限
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
