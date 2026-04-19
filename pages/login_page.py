class LoginPage:
    def __init__(self, page):
        self.page = page

    def open(self):
        """開啟登入頁面"""
        self.page.goto("https://www.saucedemo.com/")

        # 等 UI 完全載入
        self.page.wait_for_selector("#user-name")

    def login(self, username: str, password: str):
        """執行登入流程"""

        # 確保還在 Login page
        self.page.wait_for_selector("#user-name")

        # 輸入帳號
        self.page.fill("#user-name", username)

        # 輸入密碼
        self.page.fill("#password", password)

        # 點擊登入按鈕
        self.page.click("#login-button")

        # 等待頁面跳轉
        self.page.wait_for_url("**/inventory.html")