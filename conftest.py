import pytest
from playwright.sync_api import sync_playwright


# =========================
# CLI options（一定放最上層）
# =========================
def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="run tests with slow motion"
    )


# =========================
# Browser fixture
# =========================
@pytest.fixture
def page(request):
    slow = request.config.getoption("--slow")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=1000 if slow else 0
        )

        context = browser.new_context()
        page = context.new_page()

        yield page

        browser.close()