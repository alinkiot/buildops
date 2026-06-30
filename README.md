# BuildOps · 施工企业全流程智能托管平台

> **Full-lifecycle Operations Platform for Construction Enterprises**
> 一体化覆盖项目、招投标、资质、资料、成本、财税、回款、劳务与风险预警的施工企业数字化运营平台。

BuildOps 面向施工企业，将经营全链路搬到线上：从项目立项、招投标、资质合规，到工程资料、成本、财税、回款清欠与劳务法务，并以统一的**预警中心**与**经营驾驶舱**实现跨模块风险联动与数据汇总。

## 功能模块

- **系统底座**：多租户隔离，组织 / 用户 / 角色权限管理，操作审计留痕。
- **项目中心**：项目台账与甲方管理，合同额、回款、成本、工期全维度跟踪。
- **招投标**：标讯台账、资质准入校验、保证金到期扫描、投标看板与中标率统计。
- **资质合规**：企业 / 人员资质档案，资质核验与到期扫描预警。
- **工程资料**：资料模板套用、上传审核、缺项扫描、完整度统计与组卷归档。
- **成本管理**：预算编制、支出登记与审批、成本偏差与超预算预警。
- **财税账本**：收支记账、无票风险扫描、税费与利润表。
- **回款清欠**：应收台账、催收记录、回款登记（同步财税）、逾期分级与催款函 / 律师函。
- **劳务法务**：工人档案、劳动合同 / 工伤保险台账、工资发放、用工风险扫描。
- **文件中心**：统一文件库，密级分级管理、在线预览与下载审计。
- **预警中心**：规则化风险扫描（资质到期、超预算、财税无票、资料缺项、债权逾期、用工风险等），处理闭环并全程留痕。
- **经营驾驶舱**：在建项目、合同额、回款、毛利、待办预警等核心指标一屏汇总，可按模块下钻；关键列表支持 CSV 导出。

## 平台能力

- **数据范围（按项目授权）**：数据范围为 `project` 的用户（如项目负责人）仅能访问被授权项目及其成本 / 财税 / 回款 / 资料等数据；超管与全局角色不受限。授权在「系统设置 → 用户管理 → 项目授权」维护。
- **第三方集成框架**：短信 / 电子签 / OCR 采用 provider 抽象 + Mock 实现，默认 `mock` 不外发数据、全程留痕；通过环境变量 `APP_SMS_PROVIDER`/`APP_ESIGN_PROVIDER`/`APP_OCR_PROVIDER` 切换真实厂商。入口在「系统设置 → 第三方集成」。

## 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PyJWT · passlib(pbkdf2_sha256) |
| 数据库 | 默认 SQLite；`APP_DATABASE_URL` 可切换 PostgreSQL / MySQL |
| 前端 | React 18 · TypeScript · Vite · Ant Design 5 · axios · react-router |

统一响应结构 `{ code, message, data }`；分页 `{ items, page, page_size, total }`。
多租户通过 `tenant_id` 逻辑隔离；数据密级分为 public / internal / sensitive / classified，涉密文件下载需 `file:classified:view` 权限。

## 目录结构

```
backend/
  app/
    core/        配置、JWT 与密码安全
    db/          引擎与会话
    models/      SQLAlchemy 模型 + 枚举
    schemas/     Pydantic 请求/响应 + 统一响应/分页
    api/         deps（鉴权/权限/审计）+ routes（各业务模块路由）
    main.py      应用入口（含前端静态资源托管）
    seed.py      种子数据
frontend/
  src/
    api/         axios 客户端 + 类型
    auth/        登录态 Context + 权限判断
    components/  主框架布局与菜单
    pages/       登录、驾驶舱、项目、资质、资料、成本、财税、回款、文件、预警、系统设置
docs/            设计文档（PRD / 详细需求 / MVP 范围 / 页面原型）
```

## Docker 运行（推荐）

```bash
docker compose up -d --build
```

单镜像同时提供前端页面与 `/api` 接口，访问 http://localhost:8000 ；数据库与上传文件持久化到 `/data` 卷。生产部署请通过环境变量 `APP_SECRET_KEY` 注入强随机密钥。

## 本地启动

后端：

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

前端：

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 ，已配置 /api 代理到 :8000
```

## 演示账号

| 账号 | 密码 | 角色 | 说明 |
|------|------|------|------|
| admin | admin123 | 系统管理员（超管） | 全部权限 |
| boss  | boss123  | 企业老板 | 只读全局菜单 |
| pm    | pm123    | 项目负责人 | 项目 / 资料 / 文件 / 预警维护 |

## 安全说明

- JWT 鉴权，角色权限 + 按项目数据范围双重管控。
- 数据密级分级，涉密文件访问需专项权限并记录下载审计。
- 多租户逻辑隔离，所有维护类操作写入操作审计日志。
- 生产部署请通过环境变量 `APP_SECRET_KEY` 注入强随机密钥。
