def mock_payment_success(page):
    """攔截 payment API → 回傳成功"""

    page.route("**/mock/payment", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"status": "success", "message": "payment approved"}'
    ))


def mock_payment_fail(page):
    """攔截 payment API → 回傳失敗"""

    page.route("**/mock/payment", lambda route: route.fulfill(
        status=400,
        content_type="application/json",
        body='{"status": "failed", "message": "payment rejected"}'
    ))
