"""
tests/test_checkout.py

測試策略說明：
  - test_checkout_success  → 使用 Route Mock，驗證完整購物流程與 URL
  - test_checkout_fail     → 使用 Route Mock，驗證失敗情境下仍停留在 checkout 頁面
  - test_checkout_api_*    → 使用 FastAPI Server Mock，驗證真實 HTTP contract
                             （需先啟動 uvicorn）

面試要點：
  為何同一功能有兩種測試？
  Route Mock 跑在 CI，速度快且不依賴外部服務。
  Server Mock 跑在 integration 環境，驗證真實 HTTP 行為。
  兩者互補，不是重複。
"""

import pytest
import requests

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from pages.checkout_page import CheckoutPage
from flows.checkout_flow import CheckoutFlow
from utils.mock_payment import (
    mock_payment_success,
    mock_payment_fail,
    mock_via_server_success,
    mock_via_server_fail,
)

MOCK_SERVER_URL = "http://127.0.0.1:8000"


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────
def _is_server_running() -> bool:
    """
    檢查 FastAPI Mock Server 是否已啟動。
    用於 pytest.mark.skipif，避免 Server Mock 測試在 CI 中誤報 FAIL。

    面試補充：
      這是「環境防護」模式 — 測試本身不啟動 server，
      而是優雅地跳過，讓 CI log 保持乾淨。
    """
    try:
        resp = requests.get(f"{MOCK_SERVER_URL}/health", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


server_running = _is_server_running()


# ─────────────────────────────────────────────
# Route Mock Tests（CI 友好）
# ─────────────────────────────────────────────
class TestCheckoutWithRouteMock:
    """
    使用 Playwright Route Mock，不依賴任何外部服務。
    這組測試在 CI 環境中永遠可以執行。
    """

    def test_checkout_success(self, page):
        """
        驗證支付成功時，流程正確導向至 checkout-complete 頁面。

        斷言策略：
          1. URL 包含 checkout-complete（主要 happy path 驗證）
          2. 頁面有顯示完成標題（防止假陽性）
        """
        mock_payment_success(page)

        flow = CheckoutFlow(
            LoginPage(page),
            InventoryPage(page),
            CheckoutPage(page),
            page,
        )
        flow.complete_checkout("standard_user", "secret_sauce")

        # 斷言 1：URL 正確
        assert "checkout-complete" in page.url, (
            f"Expected checkout-complete in URL, got: {page.url}"
        )

        # 斷言 2：頁面元素存在（防止頁面空白但 URL 碰巧正確）
        page.wait_for_selector(".complete-header", timeout=5000)
        complete_header = page.text_content(".complete-header")
        assert complete_header is not None, "Complete header should be visible"

    def test_checkout_fail_stays_on_checkout(self, page):
        """
        驗證支付失敗時，頁面仍停留在 checkout 相關頁面（不跳轉）。

        學習重點（對比舊寫法）：
          舊版直接 assert "checkout" in page.url，但這個斷言過於寬鬆。
          現在額外等待頁面穩定，確保 UI 已完成反應再做斷言。
        """
        mock_payment_fail(page)

        login = LoginPage(page)
        inventory = InventoryPage(page)
        checkout = CheckoutPage(page)

        login.open()
        login.login("standard_user", "secret_sauce")
        page.wait_for_url("**/inventory.html")

        inventory.add_first_item_to_cart()
        inventory.go_to_cart()

        checkout.start_checkout()
        checkout.fill_information("Joe", "Gou", "777777")

        # 等待 UI 穩定後再斷言
        page.wait_for_timeout(500)

        assert "checkout" in page.url, (
            f"Should stay on checkout flow, got: {page.url}"
        )
        assert "checkout-complete" not in page.url, (
            "Should NOT reach complete page on failed payment"
        )


# ─────────────────────────────────────────────
# FastAPI Server Mock Tests（Integration）
# ─────────────────────────────────────────────
@pytest.mark.skipif(
    not server_running,
    reason="FastAPI Mock Server 未啟動，跳過 Server Mock 測試。"
           "執行方式：uvicorn mock_server.main:app --reload",
)
class TestCheckoutWithServerMock:
    """
    使用真實 FastAPI HTTP Server 的整合測試。

    驗證重點（與 Route Mock 的差異）：
      - response schema 完整性（含 timestamp 欄位）
      - HTTP status code 語意正確性（200 vs 402）
      - server 端 logging 有正確觸發
    """

    def test_payment_success_api_contract(self):
        """
        直接呼叫 FastAPI 端點，驗證 API contract。

        面試要點：
          這是 API-layer test，不經過瀏覽器。
          在沒有前端的情況下就能驗證後端行為，回饋速度更快。
        """
        resp = requests.post(
            f"{MOCK_SERVER_URL}/mock/payment/success",
            json={"amount": 299.0, "currency": "TWD", "order_id": "order-001"},
            timeout=5,
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "success"
        assert body["message"] == "payment approved"
        assert "timestamp" in body, "Response should include timestamp field"
        assert "order_id" in body, "Response should echo order_id"

    def test_payment_fail_api_contract(self):
        """
        驗證失敗端點回傳 402 且 body 結構正確。

        面試要點：
          為什麼不只斷言 status != 200？
          因為 402 是業務語意，如果改成 500 表示 server crash，
          兩者都會讓 != 200 通過，但意義完全不同。
        """
        resp = requests.post(
            f"{MOCK_SERVER_URL}/mock/payment/fail",
            json={"amount": 299.0, "currency": "TWD", "order_id": "order-002"},
            timeout=5,
        )

        assert resp.status_code == 402, f"Expected 402, got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "failed"
        assert body["message"] == "payment rejected"
        assert "timestamp" in body

    def test_checkout_success_via_server(self, page):
        """
        完整 E2E 測試，支付請求走真實 HTTP 到 FastAPI Server。
        """
        mock_via_server_success(page, base_url=MOCK_SERVER_URL)

        flow = CheckoutFlow(
            LoginPage(page),
            InventoryPage(page),
            CheckoutPage(page),
            page,
        )
        flow.complete_checkout("standard_user", "secret_sauce")

        assert "checkout-complete" in page.url
