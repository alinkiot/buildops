# syntax=docker/dockerfile:1

# ============================================================
# BuildOps · 施工企业全流程智能托管平台
# 运行镜像：流水线已编译好前端 dist/，此处只打包后端 + 静态资源。
#
# 构建前提：项目根目录下已存在 frontend/dist/（流水线 npm run build 产出）
# 构建命令：docker build -t buildops:latest .
# ============================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_DATABASE_URL=sqlite:////data/construction_mvp.db \
    APP_UPLOAD_DIR=/data/uploads

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（层缓存）
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# 后端源码
COPY backend/app ./app

# 前端编译产物（流水线已通过 npm run build 生成 frontend/dist/）
COPY frontend/dist ./static

# 入口脚本
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data/uploads

# 非 root 运行
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
