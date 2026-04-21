import pytest
from playwright.sync_api import sync_playwright


# =========================
# CLI options（pytest 指令參數）
# =========================
def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="run tests with slow motion"
    )


# =========================
# Browser fixture（核心）
# =========================
@pytest.fixture
def page(request):
    slow = request.config.getoption("--slow")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=2000 if slow else 0
        )

        # 👉 設定畫面大小
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        yield page

        browser.close()