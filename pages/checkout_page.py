from pages.base_page import BasePage


class CheckoutPage(BasePage):

    def start_checkout(self):
        """開始結帳"""
        self.click("#checkout")

    def fill_information(self, first_name: str, last_name: str, postal_code: str):
        """填寫結帳資訊"""

        self.fill("#first-name", first_name)
        self.fill("#last-name", last_name)
        self.fill("#postal-code", postal_code)

        self.click("#continue")

    def finish_checkout(self):
        self.page.wait_for_selector("#finish")
        """完成訂單"""
        self.click("#finish")