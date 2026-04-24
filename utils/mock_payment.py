"""
utils/mock_payment.py

提供兩種 Mock 模式，測試時依需求選擇：

  模式 A — Playwright Route Mock（預設，無需啟動 server）
    用法：mock_payment_success(page)
          mock_payment_fail(page)

  模式 B — FastAPI Server Mock（需先啟動 uvicorn）
    用法：mock_via_server_success(page, base_url="http://127.0.0.1:8000")
          mock_via_server_fail(page, base_url="http://127.0.0.1:8000")

面試要點：
  兩種模式分開維護，不互相耦合。
  Route Mock 適合 CI 快速跑；Server Mock 適合驗證真實 HTTP contract。
"""

import json
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 共用常數
# ─────────────────────────────────────────────
_SUCCESS_BODY = json.dumps({
    "status": "success",
    "message": "payment approved",
    "order_id": None,
    "timestamp": "2025-01-01T00:00:00+00:00",
})

_FAIL_BODY = json.dumps({
    "status": "failed",
    "message": "payment rejected",
    "order_id": None,
    "timestamp": "2025-01-01T00:00:00+00:00",
})

_CONTENT_TYPE = "application/json"


_MOCK_URL_PATTERN = "http://localhost/mock/payment"


# ─────────────────────────────────────────────
# 模式 A：Playwright Route Mock
# ─────────────────────────────────────────────
def mock_payment_success(page) -> None:
    """
    攔截對 http://localhost/mock/payment 的請求，回傳成功 response。

    URL 設計原則：
      trigger_payment() 使用絕對路徑 http://localhost/mock/payment，
      原因是相對路徑在 saucedemo.com 的 context 裡會被解析成
      https://www.saucedemo.com/mock/payment，導致 saucedemo 回傳 HTML，
      response.json() 爆出 SyntaxError。
      改用不存在但可被 Route Mock 攔截的絕對路徑，是標準解法。
    """
    logger.debug("Route mock registered: payment success")
    page.route(
        _MOCK_URL_PATTERN,
        lambda route: route.fulfill(
            status=200,
            content_type=_CONTENT_TYPE,
            body=_SUCCESS_BODY,
        ),
    )


def mock_payment_fail(page) -> None:
    """
    攔截對 http://localhost/mock/payment 的請求，回傳失敗 response（HTTP 402）。
    """
    logger.debug("Route mock registered: payment fail")
    page.route(
        _MOCK_URL_PATTERN,
        lambda route: route.fulfill(
            status=402,
            content_type=_CONTENT_TYPE,
            body=_FAIL_BODY,
        ),
    )


# ─────────────────────────────────────────────
# 模式 B：FastAPI Server Mock（真實 HTTP）
# ─────────────────────────────────────────────
def mock_via_server_success(page, base_url: str = "http://127.0.0.1:8000") -> None:
    """
    將 /mock/payment/* 的請求代理到本地 FastAPI server 的 success 端點。

    前置條件：
      uvicorn mock_server.main:app --reload 必須在背景執行。

    面試要點：
      這讓我們可以驗證真實 HTTP 行為，包含 header、response schema、
      以及 server 端 logging 是否正確記錄 request body。
    """
    def _proxy(route):
        # 注意：route.request.post_data 可能為 None（GET 請求）
        body = route.request.post_data or "{}"
        logger.debug("Proxying to FastAPI success endpoint | body=%s", body)
        route.continue_(url=f"{base_url}/mock/payment/success")

    page.route("**/mock/payment/**", _proxy)


def mock_via_server_fail(page, base_url: str = "http://127.0.0.1:8000") -> None:
    """
    將 /mock/payment/* 的請求代理到本地 FastAPI server 的 fail 端點。
    """
    def _proxy(route):
        body = route.request.post_data or "{}"
        logger.debug("Proxying to FastAPI fail endpoint | body=%s", body)
        route.continue_(url=f"{base_url}/mock/payment/fail")

    page.route("**/mock/payment/**", _proxy)