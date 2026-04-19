from playwright.sync_api import Page


class BasePage:
    def __init__(self, page: Page):
        # Playwright 的 page 物件, 加型別後 IDE 會認得 (瀏覽器核心控制器)
        self.page = page

    def goto(self, url: str):
        """導向指定網址"""
        self.page.goto(url)

    def click(self, selector: str):
        """點擊元素"""
        self.page.click(selector)

    def fill(self, selector: str, text: str):
        """輸入文字"""
        self.page.fill(selector, text)

    def get_title(self, selector: str):
        """取得文字元素"""
        return self.page.text_content(selector)
