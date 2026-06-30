"""种子数据：初始化企业、权限、角色、用户、项目、文件、预警示例。

用法： python -m app.seed
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import (
    Alert,
    AlertRule,
    Budget,
    ClientUnit,
    CollectionLog,
    Department,
    DocItem,
    DocTemplate,
    Expense,
    FileObject,
    FinanceRecord,
    Permission,
    Project,
    Qualification,
    PayrollRecord,
    Receivable,
    Role,
    Tender,
    Tenant,
    User,
    Worker,
)
from app.models.enums import (
    AlertLevel,
    AlertSource,
    AlertStatus,
    CollectionLogType,
    DataScope,
    DebtType,
    DocStatus,
    ExpenseStatus,
    ExpenseType,
    FileStatus,
    FinanceDirection,
    FinanceStatus,
    ProjectStatus,
    QualificationStatus,
    ReceivableStatus,
    SecretLevel,
    TenderStatus,
    VerifyStatus,
    WorkerStatus,
)

# 菜单 + 操作权限定义
PERMISSIONS = [
    # 菜单
    ("dashboard", "工作台", "menu", None, "/dashboard", 1),
    ("project", "项目中心", "menu", None, "/projects", 2),
    ("tender", "招投标", "menu", None, "/tenders", 3),
    ("qualification", "资质合规", "menu", None, "/qualifications", 4),
    ("document", "工程资料", "menu", None, "/documents", 5),
    ("cost", "成本管理", "menu", None, "/costs", 6),
    ("finance", "财税账本", "menu", None, "/finance", 7),
    ("receivable", "回款清欠", "menu", None, "/receivables", 8),
    ("labor", "劳务法务", "menu", None, "/labor", 9),
    ("file", "文件中心", "menu", None, "/files", 10),
    ("alert", "预警中心", "menu", None, "/alerts", 11),
    ("system", "系统设置", "menu", None, "/system", 12),
    # 操作权限
    ("project:manage", "项目维护", "button", "project", None, 1),
    ("tender:manage", "招投标维护", "button", "tender", None, 1),
    ("qualification:manage", "资质维护", "button", "qualification", None, 1),
    ("document:manage", "资料维护", "button", "document", None, 1),
    ("document:review", "资料审核", "button", "document", None, 2),
    ("cost:manage", "成本维护", "button", "cost", None, 1),
    ("cost:approve", "成本审批", "button", "cost", None, 2),
    ("finance:manage", "财税维护", "button", "finance", None, 1),
    ("receivable:manage", "回款维护", "button", "receivable", None, 1),
    ("labor:manage", "劳务维护", "button", "labor", None, 1),
    ("file:manage", "文件维护", "button", "file", None, 1),
    ("file:classified:view", "涉密文件查看", "button", "file", None, 2),
    ("alert:manage", "预警维护", "button", "alert", None, 1),
    ("system:user:manage", "用户管理", "button", "system", None, 1),
    ("system:role:manage", "角色管理", "button", "system", None, 2),
    ("system:dept:manage", "组织管理", "button", "system", None, 3),
    ("system:audit:view", "审计日志查看", "button", "system", None, 4),
    ("integration:manage", "第三方集成", "button", "system", None, 5),
]

ALL_MENU_CODES = [p[0] for p in PERMISSIONS if p[2] == "menu"]
ALL_CODES = [p[0] for p in PERMISSIONS]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.execute(select(Tenant)).scalars().first():
            print("数据已存在，跳过种子初始化。")
            return

        # 权限
        for code, name, ptype, parent, path, sort in PERMISSIONS:
            db.add(Permission(code=code, name=name, type=ptype, parent_code=parent, path=path, sort=sort))
        db.flush()

        # 企业
        tenant = Tenant(name="示范建工集团有限公司", credit_code="91110000MA01ABCD2X", region="北京")
        db.add(tenant)
        db.flush()

        # 部门
        hq = Department(tenant_id=tenant.id, name="集团总部", sort=1)
        db.add(hq)
        db.flush()
        eng_dept = Department(tenant_id=tenant.id, parent_id=hq.id, name="工程管理部", sort=2)
        fin_dept = Department(tenant_id=tenant.id, parent_id=hq.id, name="财务部", sort=3)
        db.add_all([eng_dept, fin_dept])
        db.flush()

        # 角色
        role_admin = Role(tenant_id=tenant.id, code="admin", name="系统管理员",
                          data_scope=DataScope.ALL, remark="后台管理")
        role_boss = Role(tenant_id=tenant.id, code="boss", name="企业老板",
                         data_scope=DataScope.ALL, remark="全局经营查看")
        role_pm = Role(tenant_id=tenant.id, code="pm", name="项目负责人",
                       data_scope=DataScope.PROJECT, remark="项目维护")
        db.add_all([role_admin, role_boss, role_pm])
        db.flush()

        perms = {p.code: p for p in db.execute(select(Permission)).scalars().all()}
        role_admin.permissions = list(perms.values())
        role_boss.permissions = [perms[c] for c in ALL_MENU_CODES]
        role_pm.permissions = [
            perms[c] for c in ["dashboard", "project", "tender", "qualification", "document", "cost", "labor", "file", "alert",
                               "project:manage", "tender:manage", "qualification:manage", "document:manage",
                               "document:review", "cost:manage", "labor:manage", "file:manage", "alert:manage"]
        ]

        # 用户
        admin = User(tenant_id=tenant.id, username="admin", password_hash=hash_password("admin123"),
                     name="超级管理员", department_id=hq.id, is_superadmin=True, roles=[role_admin])
        boss = User(tenant_id=tenant.id, username="boss", password_hash=hash_password("boss123"),
                    name="王总", department_id=hq.id, roles=[role_boss])
        pm = User(tenant_id=tenant.id, username="pm", password_hash=hash_password("pm123"),
                  name="李项目", department_id=eng_dept.id, roles=[role_pm])
        db.add_all([admin, boss, pm])
        db.flush()

        # 甲方
        client_a = ClientUnit(tenant_id=tenant.id, name="北京城建发展投资公司", contact="赵工",
                              phone="13800000001", credit_rating="A")
        client_b = ClientUnit(tenant_id=tenant.id, name="某市政基础设施集团", contact="钱经理",
                              phone="13800000002", credit_rating="B")
        db.add_all([client_a, client_b])
        db.flush()

        # 项目
        today = date.today()
        projects = [
            Project(tenant_id=tenant.id, code="PRJ-2024-001", name="城市副中心综合管廊工程",
                    type="市政", region="北京", owner_id=pm.id, client_id=client_a.id,
                    contract_amount=Decimal("128000000"), received_amount=Decimal("82000000"),
                    cost_amount=Decimal("69000000"), start_date=today - timedelta(days=400),
                    plan_end_date=today + timedelta(days=200), status=ProjectStatus.ONGOING,
                    secret_level=SecretLevel.INTERNAL),
            Project(tenant_id=tenant.id, code="PRJ-2024-002", name="高新区学校建设项目",
                    type="房建", region="北京", owner_id=pm.id, client_id=client_b.id,
                    contract_amount=Decimal("56000000"), received_amount=Decimal("56000000"),
                    cost_amount=Decimal("47000000"), start_date=today - timedelta(days=700),
                    plan_end_date=today - timedelta(days=60), status=ProjectStatus.SETTLING,
                    secret_level=SecretLevel.INTERNAL),
            Project(tenant_id=tenant.id, code="PRJ-2023-018", name="国防科研楼装修工程",
                    type="装修", region="河北", owner_id=pm.id, client_id=client_a.id,
                    contract_amount=Decimal("32000000"), received_amount=Decimal("12000000"),
                    cost_amount=Decimal("20000000"), start_date=today - timedelta(days=520),
                    plan_end_date=today - timedelta(days=120), status=ProjectStatus.COLLECTING,
                    secret_level=SecretLevel.CLASSIFIED),
        ]
        db.add_all(projects)
        db.flush()

        # 数据范围：项目负责人 pm 仅授权管廊、学校两个项目（第三个国防项目不授权）
        pm.projects = [projects[0], projects[1]]

        # 文件示例（仅元数据，storage_path 占位）
        db.add_all([
            FileObject(tenant_id=tenant.id, name="综合管廊施工合同.pdf", business_type="合同",
                       project_id=projects[0].id, size=2480000, content_type="application/pdf",
                       secret_level=SecretLevel.SENSITIVE, uploader_id=admin.id,
                       storage_path="seed/contract_001.pdf", status=FileStatus.ACTIVE),
            FileObject(tenant_id=tenant.id, name="学校项目竣工验收单.pdf", business_type="竣工资料",
                       project_id=projects[1].id, size=1200000, content_type="application/pdf",
                       secret_level=SecretLevel.INTERNAL, uploader_id=admin.id,
                       storage_path="seed/check_002.pdf", status=FileStatus.ACTIVE),
        ])

        # 资质台账（含即将到期 / 已过期 示例）
        db.add_all([
            Qualification(
                tenant_id=tenant.id, name="建筑工程施工总承包", type="施工总承包", level="一级",
                cert_no="D1100012024001", issuing_authority="北京市住房和城乡建设委员会",
                scope="房屋建筑工程", region_limit="全国", valid_from=today - timedelta(days=1000),
                valid_to=today + timedelta(days=25), annual_review_date=today + timedelta(days=10),
                verify_status=VerifyStatus.VERIFIED, status=QualificationStatus.VALID,
                secret_level=SecretLevel.INTERNAL, owner_id=admin.id),
            Qualification(
                tenant_id=tenant.id, name="市政公用工程施工总承包", type="施工总承包", level="二级",
                cert_no="D1100022023045", issuing_authority="北京市住房和城乡建设委员会",
                scope="市政公用工程", region_limit="全国", valid_from=today - timedelta(days=1200),
                valid_to=today - timedelta(days=15), annual_review_date=today - timedelta(days=40),
                verify_status=VerifyStatus.VERIFIED, status=QualificationStatus.VALID,
                secret_level=SecretLevel.INTERNAL, owner_id=admin.id),
            Qualification(
                tenant_id=tenant.id, name="安全生产许可证", type="许可证", level="-",
                cert_no="(京)JZ安许证字[2022]1234", issuing_authority="北京市住房和城乡建设委员会",
                scope="施工安全生产", region_limit="北京", valid_from=today - timedelta(days=700),
                valid_to=today + timedelta(days=300),
                verify_status=VerifyStatus.UNVERIFIED, status=QualificationStatus.PENDING_VERIFY,
                secret_level=SecretLevel.INTERNAL, owner_id=pm.id),
            Qualification(
                tenant_id=tenant.id, name="涉密工程资质", type="保密资质", level="乙级",
                cert_no="MJ-2023-0099", issuing_authority="国家保密行政管理部门",
                scope="涉密工程施工", region_limit="全国", valid_from=today - timedelta(days=400),
                valid_to=today + timedelta(days=600),
                verify_status=VerifyStatus.VERIFIED, status=QualificationStatus.VALID,
                secret_level=SecretLevel.CLASSIFIED, owner_id=admin.id),
        ])

        # 资料模板库
        templates = [
            DocTemplate(tenant_id=tenant.id, name="施工组织设计", category="管理资料", specialty="土建", stage="开工", sort=1),
            DocTemplate(tenant_id=tenant.id, name="开工报告", category="管理资料", specialty="土建", stage="开工", sort=2),
            DocTemplate(tenant_id=tenant.id, name="隐蔽工程验收记录", category="验收资料", specialty="土建", stage="主体", sort=3),
            DocTemplate(tenant_id=tenant.id, name="混凝土试块报告", category="试验资料", specialty="土建", stage="主体", sort=4),
            DocTemplate(tenant_id=tenant.id, name="竣工验收报告", category="竣工资料", specialty="综合", stage="竣工", sort=5),
        ]
        db.add_all(templates)
        db.flush()

        # 项目资料条目（围绕管廊项目，含多种状态）
        p0 = projects[0].id
        db.add_all([
            DocItem(tenant_id=tenant.id, project_id=p0, name="施工组织设计", category="管理资料",
                    specialty="土建", stage="开工", required=True, status=DocStatus.APPROVED, version=1,
                    uploader_id=pm.id, reviewer_id=admin.id, due_date=today - timedelta(days=300)),
            DocItem(tenant_id=tenant.id, project_id=p0, name="开工报告", category="管理资料",
                    specialty="土建", stage="开工", required=True, status=DocStatus.PENDING_REVIEW, version=1,
                    uploader_id=pm.id, due_date=today - timedelta(days=290)),
            DocItem(tenant_id=tenant.id, project_id=p0, name="隐蔽工程验收记录", category="验收资料",
                    specialty="土建", stage="主体", required=True, status=DocStatus.PENDING_UPLOAD,
                    due_date=today - timedelta(days=5)),  # 逾期，扫描后变缺项
            DocItem(tenant_id=tenant.id, project_id=p0, name="混凝土试块报告", category="试验资料",
                    specialty="土建", stage="主体", required=True, status=DocStatus.PENDING_UPLOAD,
                    due_date=today + timedelta(days=30)),
            DocItem(tenant_id=tenant.id, project_id=p0, name="竣工验收报告", category="竣工资料",
                    specialty="综合", stage="竣工", required=False, status=DocStatus.PENDING_UPLOAD,
                    due_date=today + timedelta(days=120)),
        ])

        # 成本预算科目（管廊项目）
        db.add_all([
            Budget(tenant_id=tenant.id, project_id=p0, category="材料费", budget_amount=Decimal("40000000")),
            Budget(tenant_id=tenant.id, project_id=p0, category="人工费", budget_amount=Decimal("18000000")),
            Budget(tenant_id=tenant.id, project_id=p0, category="机械费", budget_amount=Decimal("6000000")),
            Budget(tenant_id=tenant.id, project_id=p0, category="分包费", budget_amount=Decimal("15000000")),
        ])
        # 支出记录（含一笔超预算待审批）
        db.add_all([
            Expense(tenant_id=tenant.id, project_id=p0, category="材料费", type=ExpenseType.MATERIAL,
                    amount=Decimal("35000000"), payee="中建材料供应公司", has_invoice=True,
                    status=ExpenseStatus.PAID, applicant_id=pm.id, expense_date=today - timedelta(days=180)),
            Expense(tenant_id=tenant.id, project_id=p0, category="人工费", type=ExpenseType.LABOR,
                    amount=Decimal("16000000"), payee="张班组", has_invoice=True,
                    status=ExpenseStatus.PAID, applicant_id=pm.id, expense_date=today - timedelta(days=120)),
            Expense(tenant_id=tenant.id, project_id=p0, category="机械费", type=ExpenseType.MACHINE,
                    amount=Decimal("5500000"), payee="华东机械租赁", has_invoice=True,
                    status=ExpenseStatus.PAID, applicant_id=pm.id, expense_date=today - timedelta(days=90)),
            Expense(tenant_id=tenant.id, project_id=p0, category="分包费", type=ExpenseType.SUBCONTRACT,
                    amount=Decimal("12000000"), payee="基础工程分包队", has_invoice=True,
                    status=ExpenseStatus.PAID, applicant_id=pm.id, expense_date=today - timedelta(days=150)),
            Expense(tenant_id=tenant.id, project_id=p0, category="分包费", type=ExpenseType.SUBCONTRACT,
                    amount=Decimal("500000"), payee="零星用工", has_invoice=False,
                    status=ExpenseStatus.REGISTERED, applicant_id=pm.id, expense_date=today - timedelta(days=20)),
            Expense(tenant_id=tenant.id, project_id=p0, category="机械费", type=ExpenseType.MACHINE,
                    amount=Decimal("1000000"), payee="塔吊增租", has_invoice=True, over_budget=True,
                    status=ExpenseStatus.PENDING_APPROVAL, applicant_id=pm.id, expense_date=today - timedelta(days=5)),
        ])
        # 回写项目已发生成本（与支出口径一致：35+16+5.5+12+0.5+1=70.0M）
        projects[0].cost_amount = Decimal("70000000")

        # 财税收支流水（管廊项目，含无票支出用于风险扫描）
        db.add_all([
            FinanceRecord(tenant_id=tenant.id, project_id=p0, direction=FinanceDirection.INCOME,
                          category="进度款", amount=Decimal("50000000"), tax_rate=Decimal("0.09"),
                          tax_amount=Decimal("4500000"), has_invoice=True, invoice_no="FP-2025-0001",
                          counterparty="北京城建发展投资公司", record_date=today - timedelta(days=200),
                          status=FinanceStatus.POSTED),
            FinanceRecord(tenant_id=tenant.id, project_id=p0, direction=FinanceDirection.INCOME,
                          category="进度款", amount=Decimal("32000000"), tax_rate=Decimal("0.09"),
                          tax_amount=Decimal("2880000"), has_invoice=True, invoice_no="FP-2025-0002",
                          counterparty="北京城建发展投资公司", record_date=today - timedelta(days=90),
                          status=FinanceStatus.POSTED),
            FinanceRecord(tenant_id=tenant.id, project_id=p0, direction=FinanceDirection.EXPENSE,
                          category="材料款", amount=Decimal("30000000"), tax_rate=Decimal("0.13"),
                          tax_amount=Decimal("3900000"), has_invoice=True, invoice_no="JP-2025-1001",
                          counterparty="中建材料供应公司", record_date=today - timedelta(days=180),
                          status=FinanceStatus.POSTED),
            FinanceRecord(tenant_id=tenant.id, project_id=p0, direction=FinanceDirection.EXPENSE,
                          category="分包款", amount=Decimal("15000000"), tax_rate=Decimal("0.09"),
                          tax_amount=Decimal("1350000"), has_invoice=True, invoice_no="JP-2025-1002",
                          counterparty="基础工程分包队", record_date=today - timedelta(days=150),
                          status=FinanceStatus.POSTED),
            FinanceRecord(tenant_id=tenant.id, project_id=p0, direction=FinanceDirection.EXPENSE,
                          category="零星支出", amount=Decimal("8000000"), tax_rate=Decimal("0"),
                          tax_amount=Decimal("0"), has_invoice=False, counterparty="零星采购",
                          record_date=today - timedelta(days=30), status=FinanceStatus.POSTED, risk_tag="无票"),
        ])

        # 回款清欠：债权台账
        receivables = [
            Receivable(tenant_id=tenant.id, project_id=projects[0].id, client_id=client_a.id,
                       debt_type=DebtType.PROGRESS, contract_no="HT-2024-001", amount=Decimal("46000000"),
                       received_amount=Decimal("0"), due_date=today + timedelta(days=30),
                       stage="正常跟进", status=ReceivableStatus.NORMAL, owner_id=pm.id),
            Receivable(tenant_id=tenant.id, project_id=projects[1].id, client_id=client_b.id,
                       debt_type=DebtType.FINAL, contract_no="HT-2024-002", amount=Decimal("8000000"),
                       received_amount=Decimal("2000000"), due_date=today - timedelta(days=100),
                       stage="对账催收", status=ReceivableStatus.PARTIAL, owner_id=pm.id),
            Receivable(tenant_id=tenant.id, project_id=projects[2].id, client_id=client_a.id,
                       debt_type=DebtType.FINAL, contract_no="HT-2023-018", amount=Decimal("20000000"),
                       received_amount=Decimal("0"), due_date=today - timedelta(days=200),
                       stage="函件催告", status=ReceivableStatus.OVERDUE, owner_id=pm.id),
            Receivable(tenant_id=tenant.id, project_id=projects[0].id, client_id=client_a.id,
                       debt_type=DebtType.WARRANTY, contract_no="HT-2024-001", amount=Decimal("6400000"),
                       received_amount=Decimal("0"), due_date=today + timedelta(days=365),
                       stage="质保期内", status=ReceivableStatus.NORMAL, owner_id=pm.id),
        ]
        db.add_all(receivables)
        db.flush()
        # 催收日志（针对国防项目尾款）
        db.add_all([
            CollectionLog(tenant_id=tenant.id, receivable_id=receivables[2].id, type=CollectionLogType.PHONE,
                          content="电话联系甲方财务，对方称走流程审批中", result="待回款",
                          operator_id=pm.id, operator_name=pm.name),
            CollectionLog(tenant_id=tenant.id, receivable_id=receivables[2].id, type=CollectionLogType.LETTER,
                          content="寄送书面催款函并保留送达回执", result="已送达",
                          operator_id=pm.id, operator_name=pm.name),
        ])

        # 招投标：标讯/投标项目
        db.add_all([
            Tender(tenant_id=tenant.id, name="经开区道路改造工程施工招标", source="中国招标投标公共服务平台",
                   project_type="市政", region="北京", qualification_req="市政公用工程施工总承包",
                   region_req="北京", registration_deadline=today + timedelta(days=10),
                   bid_open_time=today + timedelta(days=20), deposit_amount=Decimal("500000"),
                   status=TenderStatus.PENDING_EVAL, owner_id=pm.id),
            Tender(tenant_id=tenant.id, name="某产业园厂房建设总承包招标", source="地方公共资源交易中心",
                   project_type="房建", region="河北", qualification_req="建筑工程施工总承包 安全生产许可证",
                   region_req="全国", registration_deadline=today + timedelta(days=5),
                   bid_open_time=today + timedelta(days=15), deposit_amount=Decimal("800000"),
                   status=TenderStatus.PENDING_EVAL, owner_id=pm.id),
            Tender(tenant_id=tenant.id, name="高速公路隧道专项工程招标", source="省交通厅",
                   project_type="公路", region="山西", qualification_req="公路工程施工总承包 隧道专业承包",
                   registration_deadline=today - timedelta(days=2),
                   status=TenderStatus.CANNOT_BID, eval_reason="缺少满足『公路工程施工总承包』的有效资质",
                   deposit_amount=Decimal("0"), owner_id=pm.id),
            Tender(tenant_id=tenant.id, name="老旧小区管网改造工程", source="中国招标投标公共服务平台",
                   project_type="市政", region="北京", qualification_req="市政公用工程施工总承包",
                   registration_deadline=today - timedelta(days=60), bid_open_time=today - timedelta(days=50),
                   deposit_amount=Decimal("300000"), deposit_due=today - timedelta(days=10),
                   deposit_returned=False, status=TenderStatus.WON, win_amount=Decimal("18000000"), owner_id=pm.id),
            Tender(tenant_id=tenant.id, name="市政广场景观提升工程", source="地方公共资源交易中心",
                   project_type="市政", region="北京", qualification_req="市政公用工程施工总承包",
                   registration_deadline=today - timedelta(days=90), bid_open_time=today - timedelta(days=80),
                   deposit_amount=Decimal("400000"), deposit_due=today - timedelta(days=40),
                   deposit_returned=True, status=TenderStatus.LOST,
                   fail_reason="报价高于第二名", competitor_info="本地某建工集团中标", owner_id=pm.id),
        ])

        # 劳务：工人档案（含无合同/保险缺失风险）+ 工资记录
        workers = [
            Worker(tenant_id=tenant.id, project_id=projects[0].id, name="张建国", id_card="110101199003071234",
                   team="钢筋一班", craft="钢筋工", entry_date=today - timedelta(days=120),
                   status=WorkerStatus.ONSITE, contract_signed=True,
                   insurance_expiry=today + timedelta(days=200), bank_account="6222****1234", owner_id=pm.id),
            Worker(tenant_id=tenant.id, project_id=projects[0].id, name="李大山", id_card="130202198805123456",
                   team="混凝土班", craft="普工", entry_date=today - timedelta(days=80),
                   status=WorkerStatus.ONSITE, contract_signed=False,  # 无合同 → 风险
                   insurance_expiry=today + timedelta(days=100), owner_id=pm.id),
            Worker(tenant_id=tenant.id, project_id=projects[0].id, name="王师傅", id_card="370303197512098765",
                   team="模板班", craft="木工", entry_date=today - timedelta(days=200),
                   status=WorkerStatus.ONSITE, contract_signed=True,
                   insurance_expiry=today - timedelta(days=10), owner_id=pm.id),  # 保险过期 → 风险
            Worker(tenant_id=tenant.id, project_id=projects[1].id, name="赵铁柱", id_card="140404199201011111",
                   team="架子班", craft="架子工", entry_date=today - timedelta(days=30),
                   status=WorkerStatus.ONSITE, contract_signed=False,  # 无合同 + 未参保 → 双风险
                   insurance_expiry=None, owner_id=pm.id),
            Worker(tenant_id=tenant.id, project_id=projects[1].id, name="孙离场", id_card="150505198001019999",
                   team="钢筋一班", craft="钢筋工", entry_date=today - timedelta(days=400),
                   status=WorkerStatus.LEFT, contract_signed=True,
                   insurance_expiry=today - timedelta(days=50), owner_id=pm.id),  # 已离场，不计风险
        ]
        db.add_all(workers)
        db.flush()
        db.add_all([
            PayrollRecord(tenant_id=tenant.id, worker_id=workers[0].id, period="2026-05",
                          amount=Decimal("9800"), paid=True, pay_date=today - timedelta(days=10),
                          bank_flow_no="DF20260605001"),
            PayrollRecord(tenant_id=tenant.id, worker_id=workers[1].id, period="2026-05",
                          amount=Decimal("7600"), paid=False),  # 待发
            PayrollRecord(tenant_id=tenant.id, worker_id=workers[2].id, period="2026-05",
                          amount=Decimal("8800"), paid=False),  # 待发
        ])

        # 预警规则
        rules = [
            AlertRule(tenant_id=tenant.id, code="R-001", name="资质到期提醒",
                      source=AlertSource.QUALIFICATION, level=AlertLevel.HIGH),
            AlertRule(tenant_id=tenant.id, code="R-003", name="支出超预算",
                      source=AlertSource.COST, level=AlertLevel.HIGH),
            AlertRule(tenant_id=tenant.id, code="R-005", name="资料缺项逾期",
                      source=AlertSource.DOCUMENT, level=AlertLevel.MEDIUM),
            AlertRule(tenant_id=tenant.id, code="R-006", name="债权逾期升级",
                      source=AlertSource.RECEIVABLE, level=AlertLevel.CRITICAL),
        ]
        db.add_all(rules)
        db.flush()

        # 预警事项
        db.add_all([
            Alert(tenant_id=tenant.id, rule_id=rules[0].id, source=AlertSource.QUALIFICATION,
                  title="建筑工程施工总承包一级资质将于 30 天后到期", level=AlertLevel.HIGH,
                  owner_id=admin.id, due_date=today + timedelta(days=30), status=AlertStatus.PENDING),
            Alert(tenant_id=tenant.id, rule_id=rules[1].id, source=AlertSource.COST,
                  title="管廊工程混凝土支出超预算 8%", project_id=projects[0].id, level=AlertLevel.HIGH,
                  owner_id=pm.id, due_date=today + timedelta(days=7), status=AlertStatus.PROCESSING),
            Alert(tenant_id=tenant.id, rule_id=rules[2].id, source=AlertSource.DOCUMENT,
                  title="学校项目隐蔽工程验收资料缺项", project_id=projects[1].id, level=AlertLevel.MEDIUM,
                  owner_id=pm.id, due_date=today - timedelta(days=3), status=AlertStatus.OVERDUE),
            Alert(tenant_id=tenant.id, rule_id=rules[3].id, source=AlertSource.RECEIVABLE,
                  title="国防科研楼项目尾款逾期 120 天", project_id=projects[2].id, level=AlertLevel.CRITICAL,
                  owner_id=pm.id, due_date=today + timedelta(days=5), status=AlertStatus.PENDING),
        ])

        db.commit()
        print("种子数据初始化完成。登录账号：admin/admin123、boss/boss123、pm/pm123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
