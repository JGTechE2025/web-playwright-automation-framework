"""
flows/checkout_flow.py

Flow 層職責：
  將多個 Page Object 的操作組合成完整的使用者流程。
  Flow 層不做斷言（assert 留給 Test 層），只負責流程驅動。

面試要點：
  Q: 為什麼需要 Flow 層？直接在 Test 寫不行嗎？
  A: 流程複用。5 個測試都需要「登入 → 加購物車」，
     Flow 封裝後只需維護一處。Page Object 是「操作」，Flow 是「劇本」。
"""

import logging

logger = logging.getLogger(__name__)


class CheckoutFlow:

    def __init__(self, login_page, inventory_page, checkout_page, page):
        self.login = login_page
        self.inventory = inventory_page
        self.checkout = checkout_page
        self.page = page

    def complete_checkout(self, username: str, password: str) -> None:
        """
        執行完整的結帳流程：登入 → 加商品 → 結帳 → 觸發支付 → 完成訂單。

        設計決策：
          trigger_payment() 在 fill_information() 之後、finish_checkout() 之前。
          原因：mock 需要先攔截，在使用者按 finish 之前就確認支付狀態。
        """
        logger.info("Starting checkout flow for user: %s", username)

        self.login.open()
        self.login.login(username, password)
        self.page.wait_for_url("**/inventory.html")

        self.inventory.add_first_item_to_cart()
        self.inventory.go_to_cart()

        self.checkout.start_checkout()
        self.checkout.fill_information("Joe", "Gou", "777777")

        # 先觸發 payment（讓 mock 攔截 response）
        payment_result = self.trigger_payment()
        logger.info("Payment triggered, result: %s", payment_result)

        # 等 UI 穩定後再點 finish
        self.page.wait_for_timeout(500)
        self.checkout.finish_checkout()

    def trigger_payment(self) -> dict:
        """
        從瀏覽器 context 發出支付請求，等待 response 後回傳結果。

        關鍵設計：
          使用絕對路徑 http://localhost/mock/payment，而非相對路徑。
          相對路徑在 saucedemo.com 的 context 裡會被解析成
          https://www.saucedemo.com/mock/payment，
          saucedemo 回傳 HTML 錯誤頁面，response.json() 就會爆出
          SyntaxError: Unexpected token '<'。

          Playwright Route Mock 攔截的是 URL pattern，
          只要 pattern 對到 http://localhost/mock/payment 就能攔截，
          不需要真的有 localhost server 在跑。

        面試補充：
          為什麼用 evaluate 而不是 Python 的 requests.post？
          因為支付請求必須從瀏覽器 context 發出，才能被 Playwright Route Mock 攔截。
          Python 端發出的請求走 OS network stack，bypass 掉 Playwright 的 intercept。
        """
        result = self.page.evaluate("""
            async () => {
                try {
                    const response = await fetch('http://localhost/mock/payment', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ order_id: 'order-test' })
                    });
                    return await response.json();
                } catch (e) {
                    return { status: 'error', message: e.toString() };
                }
            }
        """)
        return result or {}