# BuildOps · 施工企业全流程智能托管平台

> **Full-lifecycle Operations Platform for Construction Enterprises**
> 一体化覆盖项目、招投标、资质、资料、成本、财税、回款、劳务与风险预警的施工企业数字化运营平台。

施工企业全流程运营托管数字化系统 — MVP 首期。

基于现有设计文档（PRD / 详细需求设计 / MVP 范围冻结 / 核心页面原型 / 开发准备度评估）实现的 MVP 首期代码。

本期按《开发准备度评估》建议，先打通**低争议地基**，再逐模块铺开经营主链路。当前 MVP 已实现九大模块：

> 登录 → 系统底座（多租户 / 组织 / 用户 / 角色权限 / 操作审计） → 项目中心 → 文件中心 → 预警中心 → 经营驾驶舱

第二批业务模块（**已全部完成**）：资质合规、工程资料、成本管理、财税账本、回款清欠。
各业务模块均与**预警中心**联动（资质到期 R-001、超预算 R-003、财税无票 R-004、资料缺项 R-005、债权逾期 R-006），并在驾驶舱汇总经营口径。

V1.1 扩展模块：**招投标**（标讯台账、资质准入校验 R-002、保证金到期扫描、投标看板与中标率）、**劳务法务**（工人档案、劳动合同/工伤保险台账、工资发放、用工风险扫描 R-008）。
此外驾驶舱已深度汇总各模块经营口径（含招投标中标率、劳务用工风险），关键列表支持 CSV 导出，文件支持在线预览。

平台能力增强：
- **数据范围（按项目授权）**：角色数据范围为 `project` 的用户（如项目负责人）仅能访问被授权项目及其成本/财税/回款/资料等数据；超管与全局角色不受限。授权在「系统设置 → 用户管理 → 项目授权」维护。
- **第三方集成框架**：短信 / 电子签 / OCR 采用 provider 抽象 + Mock 实现，默认 `mock` 不外发数据，全程留痕；通过环境变量 `APP_SMS_PROVIDER`/`APP_ESIGN_PROVIDER`/`APP_OCR_PROVIDER` 切换真实厂商（需实现对应 provider 并注入密钥）。入口在「系统设置 → 第三方集成」。

## 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PyJWT · passlib(pbkdf2_sha256) |
| 数据库 | 默认 SQLite（开发）；`APP_DATABASE_URL` 可切换 PostgreSQL / MySQL |
| 前端 | React 18 · TypeScript · Vite · Ant Design 5 · axios · react-router |

统一响应结构 `{ code, message, data }`；分页 `{ items, page, page_size, total }`。
多租户通过 `tenant_id` 逻辑隔离；数据密级 public/internal/sensitive/classified；涉密文件下载需 `file:classified:view` 权限。

## 目录结构

```
backend/
  app/
    core/        配置、JWT 与密码安全
    db/          引擎与会话
    models/      SQLAlchemy 模型 + 枚举
    schemas/     Pydantic 请求/响应 + 统一响应/分页
    api/         deps（鉴权/权限/审计）+ routes（auth/system/projects/files/alerts/dashboard）
    main.py      应用入口
    seed.py      种子数据
  tests/         pytest + httpx 接口测试（77 用例）
frontend/
  src/
    api/         axios 客户端 + 类型
    auth/        登录态 Context + 权限判断
    components/  主框架布局与菜单
    pages/       登录、驾驶舱、项目、资质、资料、成本、财税、回款、文件、预警、系统设置
```

## 启动后端

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed            # 初始化演示数据（仅首次）
uvicorn app.main:app --reload --port 8000
```

- 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

切换数据库示例：

```bash
export APP_DATABASE_URL="postgresql+psycopg://user:pwd@localhost:5432/cmvp"
# 或 mysql+pymysql://user:pwd@localhost:3306/cmvp  （需另装对应驱动）
```

## 启动前端

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 ，已配置 /api 代理到 :8000
```

构建与类型检查：`npm run build`（先 `tsc --noEmit` 再 `vite build`）。

## 演示账号

| 账号 | 密码 | 角色 | 说明 |
|------|------|------|------|
| admin | admin123 | 系统管理员（超管） | 全部权限 |
| boss  | boss123  | 企业老板 | 只读全局菜单 |
| pm    | pm123    | 项目负责人 | 项目/资料/文件/预警维护 |

## 运行测试

```bash
cd backend && . .venv/bin/activate
python -m pytest -q             # 77 passed
```

测试覆盖：登录与鉴权、`/auth/me` 权限聚合、驾驶舱聚合口径、项目 CRUD 与筛选、
文件上传/下载、预警处理闭环、角色权限拦截（403）、审计日志写入、新建用户后可登录，
以及资质到期扫描、资料缺项扫描与组卷、成本超预算审批、财税无票风险扫描与利润表、回款登记同步财税与逾期分级。

## API 概览（前缀 `/api`）

| 模块 | 主要接口 |
|------|----------|
| 认证 | `POST /auth/login`、`GET /auth/me` |
| 系统设置 | `GET/POST /system/departments`、`/system/users`、`/system/roles`、`GET /system/permissions`、`GET /system/audit-logs`、`POST /system/users/{id}/reset-password`、`GET/PUT /system/users/{id}/projects`（项目授权） |
| 项目中心 | `GET/POST/PUT/DELETE /projects`、`GET/POST /projects/clients` |
| 招投标 | `GET/POST/PUT/DELETE /tenders`、`GET /tenders/board`、`POST /tenders/{id}/evaluate`、`POST /tenders/scan-deposit` |
| 资质合规 | `GET/POST/PUT/DELETE /qualifications`、`POST /qualifications/{id}/verify`、`POST /qualifications/scan` |
| 工程资料 | `GET/POST/PUT/DELETE /documents`、`/documents/templates`、`POST /documents/apply-template`、`/{id}/upload`、`/{id}/review`、`/scan`、`/completeness`、`/archive` |
| 成本管理 | `GET/POST/PUT/DELETE /costs/budgets`、`GET/POST /costs/expenses`、`POST /costs/expenses/{id}/approve`、`GET /costs/summary` |
| 财税账本 | `GET/POST/PUT/DELETE /finance`、`POST /finance/scan`、`GET /finance/profit` |
| 回款清欠 | `GET/POST/PUT/DELETE /receivables`、`GET /receivables/summary`、`POST /receivables/scan`、`/{id}/logs`、`/{id}/payment`、`/{id}/letter` |
| 劳务法务 | `GET/POST/PUT/DELETE /labor/workers`、`GET /labor/summary`、`POST /labor/scan`、`/workers/{id}/payroll` |
| 文件中心 | `GET /files`、`POST /files/upload`、`GET /files/{id}/download`、`PUT/DELETE /files/{id}` |
| 预警中心 | `GET/POST/PUT /alerts/rules`、`GET/POST /alerts`、`POST /alerts/{id}/handle` |
| 驾驶舱 | `GET /dashboard` |
| 数据导出 | `GET /export/{projects,receivables,alerts}` |
| 第三方集成 | `GET /integrations/providers`、`POST /integrations/{sms,esign,ocr}`、`GET /integrations/logs` |

## 安全说明

- JWT 默认密钥仅供开发，生产部署请通过环境变量 `APP_SECRET_KEY` 注入强随机值。
- 当前未接入 HTTPS / 速率限制 / 刷新令牌，生产前需补齐。
- 涉密文件访问已做权限校验与下载审计；更严格的密级合规（私有化部署、外发审批）属后续专项。
