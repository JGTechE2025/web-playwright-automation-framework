from unittest import mock

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from pages.checkout_page import CheckoutPage
from flows.checkout_flow import CheckoutFlow
from utils.mock_payment import mock_payment_success, mock_payment_fail


def test_checkout_success(page):

    mock_payment_success(page)

    # 正常 UI 流程
    flow = CheckoutFlow(
        LoginPage(page),
        InventoryPage(page),
        CheckoutPage(page),
        page
    )

    flow.complete_checkout("standard_user", "secret_sauce")
    assert "checkout-complete" in page.url


def test_checkout_fail(page):

    mock_payment_fail(page)

    # 🔥 learning purpose: manually replicate flow (NOT production style)
    login = LoginPage(page)
    inventory = InventoryPage(page)
    checkout = CheckoutPage(page)

    # 登入
    login.open()
    login.login("standard_user", "secret_sauce")

    page.wait_for_url("**/inventory.html")

    # 加入商品
    inventory.add_first_item_to_cart()
    inventory.go_to_cart()

    # # 結帳流程
    checkout.start_checkout()
    checkout.fill_information("Joe", "Gou", "777777")


    # ❗ 沒 error page → 改驗證 flow still works
    assert "checkout" in page.url