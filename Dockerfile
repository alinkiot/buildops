# syntax=docker/dockerfile:1

# ============================================================
# BuildOps · 施工企业全流程智能托管平台
# 纯后端镜像：前端静态资源由部署时挂载到 /app/static 目录提供。
#
# 构建：docker build -t buildops:latest .
# 运行：docker run -d -p 8574:8574 -v /path/to/dist:/app/static -v data:/data buildops:latest
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

# Python 依赖
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# 后端源码
COPY backend/app ./app

# 预创建 static 目录（部署时挂载前端产物到此目录）
RUN mkdir -p ./static

# 入口脚本
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data/uploads

# 非 root 运行
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]
EXPOSE 8574

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8574/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8574"]
