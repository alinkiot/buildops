# syntax=docker/dockerfile:1

# ============================================================
# 施工企业全流程运营托管数字化系统 (BuildOps)
# 后端运行镜像：前端已编译产物从 GitHub（私有仓库）Release 下载。
#
# 私有仓库的 release 资产必须带 Token 通过 API 下载，Token 用 BuildKit secret 注入，
# 不会残留在镜像层/历史中。构建示例：
#   GH_TOKEN=<你的PAT> DOCKER_BUILDKIT=1 docker build \
#     --secret id=gh_token,env=GH_TOKEN \
#     --build-arg FRONTEND_RELEASE_TAG=0.0.1 \
#     -t buildops:0.0.1 .
# PAT 需具备该私有库的 Contents:read（经典 token 用 repo）权限。
# ============================================================
FROM python:3.11-slim AS runtime

# 前端 release 定位参数
ARG GITHUB_REPO=alinkiot/buildops
ARG FRONTEND_RELEASE_TAG=0.0.1
ARG FRONTEND_ASSET_NAME=dist.tar.gz

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 默认将数据库与上传文件放到可挂载的 /data 卷，保证容器重建后数据不丢失
    APP_DATABASE_URL=sqlite:////data/construction_mvp.db \
    APP_UPLOAD_DIR=/data/uploads

WORKDIR /app

# curl/ca-certificates 下载资产；jq 解析 release JSON；curl 兼作 HEALTHCHECK
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates jq \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（层缓存）
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# 后端源码
COPY backend/app ./app

# 通过 GitHub API 下载私有 release 资产并解压到 ./static（main.py 会自动挂载）
# Token 经 BuildKit secret 注入，不进入镜像历史；兼容包内含 dist/ 目录或直接为文件两种结构
RUN --mount=type=secret,id=gh_token set -eux; \
    TOKEN="$(cat /run/secrets/gh_token)"; \
    API="https://api.github.com/repos/${GITHUB_REPO}"; \
    ASSET_ID="$(curl -fsSL -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
        "${API}/releases/tags/${FRONTEND_RELEASE_TAG}" \
        | jq -r --arg n "${FRONTEND_ASSET_NAME}" '.assets[] | select(.name==$n) | .id')"; \
    test -n "${ASSET_ID}" && test "${ASSET_ID}" != "null"; \
    curl -fSL -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/octet-stream" \
        "${API}/releases/assets/${ASSET_ID}" -o /tmp/dist.tar.gz; \
    mkdir -p /tmp/fe ./static; \
    tar -xzf /tmp/dist.tar.gz -C /tmp/fe; \
    if [ -d /tmp/fe/dist ]; then cp -a /tmp/fe/dist/. ./static/; else cp -a /tmp/fe/. ./static/; fi; \
    test -f ./static/index.html; \
    rm -rf /tmp/dist.tar.gz /tmp/fe

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
