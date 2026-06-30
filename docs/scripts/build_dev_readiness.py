from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from build_prd import BLUE, INK, MUTED, add_table, bullet, heading, para, set_font


OUT = Path("施工企业全流程运营托管数字化系统_开发准备度评估与实施建议.docx")


def setup(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1

    hp = section.header.paragraphs[0]
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(hp.add_run("开发准备度评估"), size=9, color=MUTED)

    fp = section.footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_font(fp.add_run("施工企业全流程运营托管数字化系统"), size=9, color=MUTED)


def title_block(doc: Document) -> None:
    para(doc, "", after=8)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    set_font(p.add_run("开发准备度评估与实施建议"), size=23, color=RGBColor(0, 0, 0), bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    set_font(p.add_run("施工企业全流程运营托管数字化系统"), size=15, color=RGBColor(55, 55, 55))
    for label, value in [
        ("评估依据:", "现有 PRD 与详细需求设计说明书"),
        ("评估结论:", "可进入开发准备与 MVP 原型设计；不建议直接进入全量编码开发"),
        ("建议路径:", "先做 MVP 范围冻结、原型、技术架构、数据库/API 设计、测试用例，再启动开发迭代"),
        ("生成日期:", date.today().isoformat()),
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(label + " ")
        set_font(r, size=11, color=INK, bold=True)
        set_font(p.add_run(value), size=11, color=INK)
    rule = doc.add_paragraph()
    p_pr = rule._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "2E74B5")
    pbdr.append(bottom)
    p_pr.append(pbdr)


def build() -> None:
    doc = Document()
    setup(doc)
    title_block(doc)

    heading(doc, "1. 总体判断", 1)
    para(
        doc,
        "基于现有 PRD 和详细需求设计，项目已经具备“进入开发准备阶段”的条件，但尚不具备“直接进入全量编码开发”的成熟度。当前文档已经清楚描述了业务价值、目标用户、九大模块、核心流程、字段方向、规则预警、权限和验收口径，可以支撑产品评审、MVP 立项、原型设计和技术方案设计。",
    )
    para(
        doc,
        "如果现在直接让研发开工，风险主要集中在：范围过大、页面交互未定、数据库/API 未定、第三方接口未确认、涉密合规边界未确认、MVP 优先级仍需冻结。因此建议先进入“开发前置设计冲刺”，完成关键技术与交互交付物后，再进行迭代开发。",
    )

    heading(doc, "2. 开发准备度评分", 1)
    add_table(
        doc,
        ["维度", "当前状态", "评分", "说明"],
        [
            ("业务需求清晰度", "较充分", "85/100", "痛点、模块、角色、业务流程、验收方向已经明确。"),
            ("MVP 范围", "需冻结", "65/100", "已有分期建议，但需明确首期具体页面、功能、接口和不做事项。"),
            ("交互原型", "缺失", "30/100", "尚未形成页面结构、操作路径、表单字段、列表筛选和看板布局。"),
            ("数据模型", "初步", "55/100", "已有核心对象和字段方向，但缺少 ER 图、字段类型、索引、枚举和约束。"),
            ("接口/API", "缺失", "25/100", "尚未定义前后端 API、第三方接口、鉴权、错误码和数据同步策略。"),
            ("技术架构", "缺失", "30/100", "未确定前后端技术栈、部署方式、文件存储、权限模型和多租户方案。"),
            ("测试验收", "初步", "60/100", "已有验收口径，但需转成测试用例、边界条件和验收数据。"),
            ("合规安全", "需专项确认", "50/100", "涉密、审计、数据隔离方向明确，但需法务/保密顾问确认边界。"),
        ],
        [1800, 1800, 1000, 4760],
    )
    para(doc, "综合判断：当前开发准备度约为 55-65%。适合启动 MVP 原型与技术设计，不适合直接启动完整九大模块开发。")

    heading(doc, "3. 已具备开发基础的内容", 1)
    for item in [
        "产品定位清晰：建工全链条合规 + 盈利托管一体化 SaaS。",
        "用户角色清晰：老板、总经理、项目负责人、财务、资料员、资质/人事、投标、法务/清欠、涉密管理员。",
        "业务模块清晰：资质、财税、投标、资料、成本、劳务法务、回款、驾驶舱、人员升级并购九大模块。",
        "核心价值清晰：合规前置、风险预警、资料留痕、成本控制、回款闭环、经营驾驶舱。",
        "MVP 方向基本清晰：优先做资质/资料/成本/财税/回款/驾驶舱，招投标、劳务法务、并购升级可分期建设。",
        "验收方向清晰：预警可触发、数据可追溯、权限可隔离、报表可下钻、关键流程可闭环。",
    ]:
        bullet(doc, item)

    heading(doc, "4. 暂不建议直接开发的原因", 1)
    add_table(
        doc,
        ["问题", "影响", "建议补充"],
        [
            ("范围过大", "九大模块同时开发会导致周期长、预算高、验收困难", "冻结 MVP，只保留首期高价值闭环"),
            ("页面未设计", "研发无法准确判断列表、表单、看板、审批、详情页怎么做", "输出高保真或低保真原型"),
            ("数据结构未定", "容易出现字段反复、统计口径不一致、后期重构", "输出 ER 图、数据字典、枚举字典"),
            ("接口未定义", "前后端协作困难，第三方对接风险不可控", "输出 API 文档和接口优先级"),
            ("权限模型复杂", "涉密、营收、项目、角色、导出审批若后补，改造成本高", "先设计 RBAC + 数据密级 + 项目授权"),
            ("合规边界未确认", "军工涉密与清欠法务场景有专业风险", "请保密/法务/财税顾问确认边界"),
        ],
        [1900, 3600, 3860],
    )

    heading(doc, "5. 建议的 MVP 开发范围", 1)
    add_table(
        doc,
        ["模块", "首期建议做", "首期暂不做"],
        [
            ("企业/项目/权限底座", "企业、组织、项目、角色、权限、文件、日志、预警中心", "复杂组织绩效、复杂 BI 权限"),
            ("资质合规", "资质台账、证书到期、核验记录、年审预警", "资质并购复杂交易流程"),
            ("工程资料", "资料目录、模板、上传、审核、缺项预警、组卷导出", "CAD 深度在线编辑"),
            ("项目成本", "预算、支出、超预算审批、分包付款、利润核算", "复杂 ERP 财务凭证自动化"),
            ("财税风控", "项目账本、发票记录、税负提示、基础报表", "深度税务申报接口"),
            ("回款清欠", "债权建档、证据链、催收记录、文书模板、回款阶段", "诉讼代理全流程自动化"),
            ("驾驶舱", "经营总览、项目利润、待回款、风险预警、资质临期", "复杂自定义 BI 报表"),
        ],
        [1700, 4300, 3360],
    )

    heading(doc, "6. 开发前必须补齐的交付物", 1)
    add_table(
        doc,
        ["交付物", "目的", "负责人建议", "是否必须"],
        [
            ("MVP 范围清单", "明确首期做什么、不做什么、验收边界", "产品负责人 + 业务方", "必须"),
            ("页面原型", "明确页面布局、字段、操作路径、状态提示", "产品经理/UI", "必须"),
            ("数据字典/ER 图", "明确表结构、字段类型、枚举、关系、约束", "后端架构师", "必须"),
            ("API 文档", "明确前后端接口、参数、返回、错误码、鉴权", "后端 + 前端", "必须"),
            ("权限矩阵", "明确角色可见、可编辑、可导出、可审批的数据范围", "产品 + 架构师", "必须"),
            ("测试用例", "把验收标准转成可执行测试步骤", "测试负责人", "必须"),
            ("技术架构方案", "确定技术栈、部署、存储、审计、多租户、安全", "技术负责人", "必须"),
            ("第三方接口调研", "确认电子签、OCR、消息、招标、发票、人脸等能力", "产品 + 技术", "建议"),
        ],
        [1900, 3500, 2200, 1760],
    )

    heading(doc, "7. 建议实施路线", 1)
    add_table(
        doc,
        ["阶段", "周期建议", "核心产出"],
        [
            ("需求冻结", "3-5 天", "MVP 功能清单、优先级、不做清单、验收边界"),
            ("原型设计", "5-10 天", "核心页面原型、操作流程、字段清单、权限矩阵"),
            ("技术设计", "5-10 天", "架构方案、ER 图、API 文档、部署方案、接口调研"),
            ("MVP 开发", "6-10 周", "底座 + 资质 + 资料 + 成本 + 财税 + 回款 + 驾驶舱基础版"),
            ("试点验证", "2-4 周", "导入真实企业/项目数据，验证预警、报表、权限、流程闭环"),
            ("迭代扩展", "持续", "招投标、劳务法务、涉密增强、人员升级并购、智能分析"),
        ],
        [1800, 1400, 6160],
    )

    heading(doc, "8. 结论", 1)
    para(
        doc,
        "现有文档已经具备产品立项、需求评审、MVP 范围讨论和研发估算的基础，但还没有达到直接编码开发所需的颗粒度。最稳妥的推进方式是：以现有 PRD 和详细需求设计为需求蓝本，立即补做 MVP 原型、数据模型、接口文档、权限矩阵和测试用例。补齐后即可进入开发。",
    )
    para(
        doc,
        "若必须马上启动开发，建议只启动“技术底座 + 企业项目中心 + 文件中心 + 权限审计 + 预警中心”这类低争议基础能力，同时并行完成业务模块原型与详细技术设计。",
    )

    doc.save(OUT)


if __name__ == "__main__":
    build()
