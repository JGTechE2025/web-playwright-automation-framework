from pages.base_page import BasePage


class InventoryPage(BasePage):
    def add_first_item_to_cart(self):
        """加入第一個商品到購物車"""
        self.click("#add-to-cart-sauce-labs-backpack")

    def go_to_cart(self):
        """前往購物車"""
        self.click(".shopping_cart_link")