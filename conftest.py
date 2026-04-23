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
    # 👉 關鍵：從 pytest 的參數抓取 headless 設定 (預設是 True)
    # 如果你下指令時沒加 --headed，在 CI 就會自動跑 headless
    is_headless = not request.config.getoption("--headed")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_headless,  # 改為動態判斷
            slow_mo=2000 if slow else 0
        )

        # 設定畫面大小
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()
        yield page
        browser.close()