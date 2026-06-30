#!/usr/bin/env bash
set -euo pipefail

# 初始化数据库与种子数据（seed 幂等：已有数据会自动跳过）
echo "[entrypoint] 初始化数据库与演示数据 ..."
python -m app.seed || echo "[entrypoint] 种子初始化跳过/失败（可能数据库已初始化）"

echo "[entrypoint] 启动服务: $*"
exec "$@"
