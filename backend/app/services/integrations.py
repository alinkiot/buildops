"""第三方集成服务：短信 / 电子签 / OCR 的 provider 抽象与 Mock 实现。

设计要点：
- 通过配置（APP_SMS_PROVIDER / APP_ESIGN_PROVIDER / APP_OCR_PROVIDER）切换 provider。
- 默认 mock，不进行任何外部网络调用、不外发数据。
- 接入真实厂商时：新增对应 Provider 子类（在内部用 httpx 调用厂商 API 并注入密钥），
  并在工厂函数 _build_* 中注册厂商代号即可，无需改动路由与留痕逻辑。
"""
from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings


class ProviderError(Exception):
    """provider 未实现或调用失败。"""


# ---------------- 短信 ----------------
class SmsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def send(self, to: str, content: str) -> dict[str, Any]:
        ...


class MockSmsProvider(SmsProvider):
    name = "mock"

    def send(self, to: str, content: str) -> dict[str, Any]:
        # 模拟发送：生成消息号，不进行真实网络调用
        return {
            "message_id": f"SMS-{uuid.uuid4().hex[:12].upper()}",
            "status": "sent",
            "to": to,
            "segments": (len(content) // 70) + 1,
            "provider": self.name,
            "note": "mock 发送，未实际下发短信",
        }


# ---------------- 电子签 ----------------
class ESignProvider(ABC):
    name: str = "base"

    @abstractmethod
    def initiate(self, doc_name: str, signers: list[str]) -> dict[str, Any]:
        ...


class MockESignProvider(ESignProvider):
    name = "mock"

    def initiate(self, doc_name: str, signers: list[str]) -> dict[str, Any]:
        flow_id = f"ESIGN-{uuid.uuid4().hex[:12].upper()}"
        return {
            "flow_id": flow_id,
            "status": "signing",
            "doc_name": doc_name,
            "signers": signers,
            "sign_url": f"https://esign.mock/sign/{flow_id}",
            "provider": self.name,
            "note": "mock 发起签署，返回模拟签署链接",
        }


# ---------------- OCR ----------------
class OcrProvider(ABC):
    name: str = "base"

    @abstractmethod
    def recognize(self, filename: str, doc_type: str, content: bytes | None = None) -> dict[str, Any]:
        ...


class MockOcrProvider(OcrProvider):
    name = "mock"

    _TEMPLATES = {
        "invoice": {"发票代码": "011001900111", "发票号码": "08319284",
                    "金额": "100000.00", "税率": "9%", "开票方": "示例供应商有限公司"},
        "contract": {"合同名称": "施工承包合同", "甲方": "某建设单位", "乙方": "示范建工集团",
                     "合同金额": "12800000.00", "签订日期": "2025-01-15"},
        "certificate": {"证书名称": "建筑工程施工总承包", "证书编号": "D110001",
                        "有效期至": "2027-12-31", "发证机关": "住建委"},
        "id_card": {"姓名": "张建国", "身份证号": "1101**********1234", "民族": "汉"},
    }

    def recognize(self, filename: str, doc_type: str, content: bytes | None = None) -> dict[str, Any]:
        fields = dict(self._TEMPLATES.get(doc_type, {"识别内容": "未配置该单据类型的识别模板"}))
        digest = hashlib.md5((content or filename.encode())).hexdigest()[:8] if content else "n/a"
        return {
            "doc_type": doc_type,
            "filename": filename,
            "fields": fields,
            "confidence": 0.98,
            "content_hash": digest,
            "provider": self.name,
            "note": "mock 识别，返回模拟字段，建议人工复核",
        }


# ---------------- 工厂 ----------------
def get_sms_provider() -> SmsProvider:
    if settings.SMS_PROVIDER == "mock":
        return MockSmsProvider()
    raise ProviderError(f"短信 provider '{settings.SMS_PROVIDER}' 尚未实现，请在 integrations.py 中注册真实厂商实现")


def get_esign_provider() -> ESignProvider:
    if settings.ESIGN_PROVIDER == "mock":
        return MockESignProvider()
    raise ProviderError(f"电子签 provider '{settings.ESIGN_PROVIDER}' 尚未实现，请在 integrations.py 中注册真实厂商实现")


def get_ocr_provider() -> OcrProvider:
    if settings.OCR_PROVIDER == "mock":
        return MockOcrProvider()
    raise ProviderError(f"OCR provider '{settings.OCR_PROVIDER}' 尚未实现，请在 integrations.py 中注册真实厂商实现")
