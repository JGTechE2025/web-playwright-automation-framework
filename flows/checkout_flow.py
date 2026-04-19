class CheckoutFlow:

    def __init__(self, login_page, inventory_page, checkout_page, page):
        self.login = login_page
        self.inventory = inventory_page
        self.checkout = checkout_page
        self.page = page

    def complete_checkout(self, username, password):
        # 登入
        self.login.open()
        self.login.login(username, password)

        self.page.wait_for_url("**/inventory.html")

        # 加商品
        self.inventory.add_first_item_to_cart()
        self.inventory.go_to_cart()

        # 結帳流程
        self.checkout.start_checkout()
        self.checkout.fill_information("Joe", "Gou", "777777")

        # 先觸發 payment (給 mock 攔截)
        self.trigger_payment()

        # 等一下讓 UI 穩定
        self.page.wait_for_timeout(1000)

        # 再點 finish (這時候才在 step-two)
        self.checkout.finish_checkout()


    def trigger_payment(self):
        """模擬前端呼叫 payment API（給 mock 用）"""

        self.page.evaluate("""
            fetch('/mock/payment', {
                method: 'POST'
            })
        """)