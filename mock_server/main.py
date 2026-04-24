"""
FastAPI Mock Server — 模擬支付 API

架構說明：
  用途：提供真實 HTTP 端點，供 E2E 測試與 API contract 驗證使用。
  與 Playwright Route Mock 的差異：
    - Route Mock  → 攔截瀏覽器請求，速度快，適合 UI 快速驗證
    - FastAPI Mock → 真正走 HTTP，可驗證 request body / header / status code

啟動指令：
  uvicorn mock_server.main:app --reload
  預設位址：http://127.0.0.1:8000
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Payment Mock Server",
    description="模擬支付成功與失敗情境，供自動化測試使用",
    version="1.0.0",
)

# ─────────────────────────────────────────────
# CORS：允許 Playwright 的瀏覽器 context 呼叫
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────
class PaymentRequest(BaseModel):
    """
    支付請求 body（選填，方便日後擴充驗證邏輯）
    面試要點：有 schema 才能做 request body 的 contract 驗證
    """
    amount: float | None = None
    currency: str | None = "TWD"
    order_id: str | None = None


class PaymentResponse(BaseModel):
    status: str
    message: str
    order_id: str | None = None
    timestamp: str


# ─────────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────────
def _now() -> str:
    """回傳 ISO 8601 時間戳，方便 assert 時間欄位存在"""
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
# 💰 Payment Success
# ─────────────────────────────────────────────
@app.post(
    "/mock/payment/success",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    tags=["payment"],
    summary="模擬支付成功",
)
async def payment_success(payload: PaymentRequest, request: Request):
    """
    模擬支付核准情境。

    設計決策：
      回傳 200 而非 201，符合多數支付閘道的慣例（非 resource creation）。
      加上 timestamp 欄位，讓測試可驗證 response 結構完整性。
    """
    logger.info(
        "Payment success triggered | order_id=%s amount=%s",
        payload.order_id,
        payload.amount,
    )
    return PaymentResponse(
        status="success",
        message="payment approved",
        order_id=payload.order_id,
        timestamp=_now(),
    )


# ─────────────────────────────────────────────
# ❌ Payment Fail
# ─────────────────────────────────────────────
@app.post(
    "/mock/payment/fail",
    response_model=PaymentResponse,
    status_code=status.HTTP_402_PAYMENT_REQUIRED,
    tags=["payment"],
    summary="模擬支付失敗",
)
async def payment_fail(payload: PaymentRequest, request: Request):
    """
    模擬支付被拒絕情境。

    設計決策：
      回傳 402 Payment Required，語意比 400 更精確。
      面試補充：真實閘道（如 Stripe）會在 body 裡帶 decline_code，
      這裡簡化為單一 message 以利測試斷言。
    """
    logger.info(
        "Payment fail triggered | order_id=%s amount=%s",
        payload.order_id,
        payload.amount,
    )
    return PaymentResponse(
        status="failed",
        message="payment rejected",
        order_id=payload.order_id,
        timestamp=_now(),
    )


# ─────────────────────────────────────────────
# 健康檢查（CI/CD pipeline 用）
# ─────────────────────────────────────────────
@app.get("/health", tags=["infra"], summary="Server 健康檢查")
async def health():
    """
    給 GitHub Actions 或 Docker healthcheck 用。
    在真正跑測試前先確認 server 已就緒。
    """
    return {"status": "ok", "timestamp": _now()}
