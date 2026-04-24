"""
tests/test_checkout.py

測試策略說明：
  - test_checkout_success  → 使用 Route Mock，驗證完整購物流程與 URL
  - test_checkout_fail     → 使用 Route Mock，驗證失敗情境下仍停留在 checkout 頁面
  - test_checkout_api_*    → 使用 FastAPI Server Mock，驗證真實 HTTP contract
                             （需先啟動 uvicorn）

Allure 裝飾器說明：
  @allure.epic     → 最高層，對應產品模組（如：電商平台）
  @allure.feature  → 功能模組（如：結帳流程）
  @allure.story    → 使用者故事（如：支付成功）
  @allure.severity → 測試重要程度（blocker > critical > normal > minor > trivial）
  @allure.step     → 在報告中顯示步驟說明（也可用 with allure.step("..."):）

面試要點：
  為什麼同一功能有兩種測試？
  Route Mock 跑在 CI，速度快且不依賴外部服務。
  Server Mock 跑在 integration 環境，驗證真實 HTTP 行為。
  兩者互補，不是重複。
"""

import allure
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
@allure.epic("電商平台自動化測試")
@allure.feature("結帳流程 (Checkout Flow)")
class TestCheckoutWithRouteMock:
    """
    使用 Playwright Route Mock，不依賴任何外部服務。
    這組測試在 CI 環境中永遠可以執行。
    """

    @allure.story("支付成功 - 完整 E2E 流程")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("""
    驗證使用者從登入到完成結帳的完整 Happy Path。
    使用 Playwright Route Mock 攔截支付請求，模擬後端回傳成功。

    前置條件：
      - 測試帳號 standard_user 可正常登入
      - Playwright Route Mock 已設定 payment success 攔截

    預期結果：
      - URL 包含 checkout-complete
      - 頁面顯示 .complete-header 元素
    """)
    def test_checkout_success(self, page):
        """
        驗證支付成功時，流程正確導向至 checkout-complete 頁面。
        """
        with allure.step("設定支付成功 Mock"):
            mock_payment_success(page)

        with allure.step("執行完整結帳流程"):
            flow = CheckoutFlow(
                LoginPage(page),
                InventoryPage(page),
                CheckoutPage(page),
                page,
            )
            flow.complete_checkout("standard_user", "secret_sauce")

        with allure.step("斷言 1：驗證 URL 包含 checkout-complete"):
            assert "checkout-complete" in page.url, (
                f"Expected checkout-complete in URL, got: {page.url}"
            )

        with allure.step("斷言 2：驗證完成頁面元素可見（防假陽性）"):
            page.wait_for_selector(".complete-header", timeout=5000)
            complete_header = page.text_content(".complete-header")
            assert complete_header is not None, "Complete header should be visible"

        # 成功截圖附加至報告（非必要，但有助於展示）
        allure.attach(
            page.screenshot(full_page=True),
            name="checkout-complete-page",
            attachment_type=allure.attachment_type.PNG,
        )

    @allure.story("支付失敗 - 頁面留在 Checkout")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("""
    驗證支付失敗時，系統不會錯誤跳轉到完成頁面。
    這個測試保護「失敗情境」不被 regression 破壞。

    預期結果：
      - URL 包含 checkout（仍在結帳流程中）
      - URL 不包含 checkout-complete（未完成訂單）
    """)
    def test_checkout_fail_stays_on_checkout(self, page):
        """
        驗證支付失敗時，頁面仍停留在 checkout 相關頁面（不跳轉）。
        """
        with allure.step("設定支付失敗 Mock（HTTP 402）"):
            mock_payment_fail(page)

        with allure.step("登入並加入商品到購物車"):
            login = LoginPage(page)
            inventory = InventoryPage(page)
            checkout = CheckoutPage(page)

            login.open()
            login.login("standard_user", "secret_sauce")
            page.wait_for_url("**/inventory.html")

            inventory.add_first_item_to_cart()
            inventory.go_to_cart()

        with allure.step("進入結帳並填寫資訊"):
            checkout.start_checkout()
            checkout.fill_information("Joe", "Gou", "777777")
            # 等待 UI 穩定後再斷言（避免 race condition）
            page.wait_for_timeout(500)

        with allure.step("斷言：仍在 checkout 流程，未跳轉至完成頁"):
            assert "checkout" in page.url, (
                f"Should stay on checkout flow, got: {page.url}"
            )
            assert "checkout-complete" not in page.url, (
                "Should NOT reach complete page on failed payment"
            )


# ─────────────────────────────────────────────
# FastAPI Server Mock Tests（Integration）
# ─────────────────────────────────────────────
@allure.epic("電商平台自動化測試")
@allure.feature("支付 API Contract 驗證")
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

    @allure.story("API Contract - 支付成功端點")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("""
    直接呼叫 FastAPI /mock/payment/success，驗證 Response Schema。
    此為 API-layer test，不經過瀏覽器，回饋速度更快。

    驗證項目：
      - HTTP Status Code = 200
      - body.status = "success"
      - body.message = "payment approved"
      - body 包含 timestamp 欄位
      - body 包含 order_id 欄位
    """)
    def test_payment_success_api_contract(self):
        """直接呼叫 FastAPI 端點，驗證 API contract。"""
        with allure.step("POST /mock/payment/success"):
            resp = requests.post(
                f"{MOCK_SERVER_URL}/mock/payment/success",
                json={"amount": 299.0, "currency": "TWD", "order_id": "order-001"},
                timeout=5,
            )

        with allure.step("附加 Response 至報告"):
            allure.attach(
                resp.text,
                name="API Response Body",
                attachment_type=allure.attachment_type.JSON,
            )

        with allure.step("斷言 HTTP Status Code = 200"):
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        with allure.step("斷言 Response Schema 完整性"):
            body = resp.json()
            assert body["status"] == "success"
            assert body["message"] == "payment approved"
            assert "timestamp" in body, "Response should include timestamp field"
            assert "order_id" in body, "Response should echo order_id"

    @allure.story("API Contract - 支付失敗端點")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("""
    驗證失敗端點回傳 402（Payment Required）且 body 結構正確。

    為什麼斷言 402 而非只斷言 != 200？
    因為 402 是業務語意（支付被拒），500 是 server crash。
    兩者都不是 200，但意義完全不同，測試必須精確區分。
    """)
    def test_payment_fail_api_contract(self):
        """驗證失敗端點回傳 402 且 body 結構正確。"""
        with allure.step("POST /mock/payment/fail"):
            resp = requests.post(
                f"{MOCK_SERVER_URL}/mock/payment/fail",
                json={"amount": 299.0, "currency": "TWD", "order_id": "order-002"},
                timeout=5,
            )

        with allure.step("附加 Response 至報告"):
            allure.attach(
                resp.text,
                name="API Response Body",
                attachment_type=allure.attachment_type.JSON,
            )

        with allure.step("斷言 HTTP Status Code = 402"):
            assert resp.status_code == 402, f"Expected 402, got {resp.status_code}"

        with allure.step("斷言 Response Schema 完整性"):
            body = resp.json()
            assert body["status"] == "failed"
            assert body["message"] == "payment rejected"
            assert "timestamp" in body

    @allure.story("支付成功 - 真實 HTTP Server E2E")
    @allure.severity(allure.severity_level.NORMAL)
    def test_checkout_success_via_server(self, page):
        """完整 E2E 測試，支付請求走真實 HTTP 到 FastAPI Server。"""
        with allure.step("設定 Server Mock Proxy（走真實 HTTP）"):
            mock_via_server_success(page, base_url=MOCK_SERVER_URL)

        with allure.step("執行完整結帳流程"):
            flow = CheckoutFlow(
                LoginPage(page),
                InventoryPage(page),
                CheckoutPage(page),
                page,
            )
            flow.complete_checkout("standard_user", "secret_sauce")

        with allure.step("斷言：URL 包含 checkout-complete"):
            assert "checkout-complete" in page.url