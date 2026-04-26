# pages/login_page.py

class LoginPage:
    # 錯誤訊息選擇器獨立成常數，未來若 selector 改變只需改一處（DRY 原則）
    _ERROR_SELECTOR = "[data-test='error']"

    def __init__(self, page):
        self.page = page

    def open(self):
        """開啟登入頁面"""
        self.page.goto("https://www.saucedemo.com/")
        self.page.wait_for_selector("#user-name")

    def login(self, username: str, password: str):
        """執行登入流程，成功時等待跳轉"""
        self.page.wait_for_selector("#user-name")
        self.page.fill("#user-name", username)
        self.page.fill("#password", password)
        self.page.click("#login-button")
        self.page.wait_for_url("**/inventory.html")

    def login_expect_failure(self, username: str, password: str):
        """
        執行登入，預期失敗用（不等待跳轉）。
        error path 不加 wait_for_url，避免 TimeoutError 蓋掉真正的斷言失敗。
        """
        self.page.wait_for_selector("#user-name")
        self.page.fill("#user-name", username)
        self.page.fill("#password", password)
        self.page.click("#login-button")

    def get_error_message(self) -> str:
        """
        取得登入錯誤訊息文字。

        【等待機制選擇】
        使用 wait_for_selector 而非 time.sleep()。
        wait_for_selector 會在元素出現時立即繼續，最多等 timeout 毫秒，
        不會像 sleep 無條件浪費時間，也不會因網路慢而提早失敗。

        面試問法：「你怎麼避免 flaky test？」
        答：用 Playwright 的內建 auto-waiting 和 wait_for_selector，
            完全不用 time.sleep，元素到了就繼續，不到就等，超時才報錯。
        """
        self.page.wait_for_selector(self._ERROR_SELECTOR)
        return self.page.text_content(self._ERROR_SELECTOR) or ""

    def is_on_login_page(self) -> bool:
        """
        確認目前仍在登入頁（用於登入失敗後的 URL 斷言）。

        【為什麼不直接在 Test 用 page.url？】
        將「什麼 URL = 登入頁」的知識封裝在 Page Object，
        若網址改變只需修改這一處，符合 POM 的「單一知識來源」原則。
        """
        return "saucedemo.com" in self.page.url and "inventory" not in self.page.url