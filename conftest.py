"""
conftest.py

職責：
  1. 管理瀏覽器生命週期（browser / page fixture）
  2. 注入 Allure 環境資訊（environment.properties）
  3. 測試失敗時自動截圖並附加至 Allure 報告

面試要點：
  Q: 為什麼截圖放在 conftest 而不是每個 test 裡？
  A: 關注點分離。Test 層只負責斷言商業邏輯，截圖是「基礎設施」行為。
     放在 conftest 的 autouse fixture 裡，所有測試自動繼承，零重複程式碼。
"""

import os
import allure
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
        help="run tests with slow motion (500ms between actions)"
    )


# =========================
# Browser fixture（核心）
# =========================
@pytest.fixture
def page(request):
    slow = request.config.getoption("--slow")
    # 從 pytest 參數抓取 headless 設定（預設 True）
    # CI 環境沒有 --headed，自動使用 headless mode
    is_headless = not request.config.getoption("--headed")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_headless,
            slow_mo=1000 if slow else 0
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()
        yield page
        browser.close()


# =========================
# Allure 自動截圖 fixture
# =========================
@pytest.fixture(autouse=True)
def attach_screenshot_on_failure(request, page):
    """
    測試結束後，若狀態為 FAILED，自動截圖並附加至 Allure 報告。

    設計決策：
      autouse=True 讓所有測試自動套用，無需逐一引入。
      截圖在 yield 之後執行（teardown 階段），確保頁面狀態已定。

    面試補充：
      為什麼用 allure.attach 而非只存檔案？
      allure.attach 直接把截圖嵌入 HTML 報告，
      閱讀報告者不需要額外找截圖檔，Debug 效率更高。
    """
    yield  # 測試執行中

    # 只在失敗時截圖，避免成功的測試產生多餘檔案
    if request.node.rep_call.failed if hasattr(request.node, 'rep_call') else False:
        try:
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name=f"FAILED - {request.node.name}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as e:
            # page 可能已經關閉，避免截圖失敗干擾測試結果
            print(f"[Warning] Screenshot failed: {e}")


# =========================
# pytest hook：追蹤每個 phase 的結果
# 讓 attach_screenshot_on_failure fixture 能讀到 rep_call
# =========================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    標準 hook，將每個 phase（setup / call / teardown）的結果
    存回 item 物件，供 fixture 中的 request.node.rep_call 讀取。
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# =========================
# Allure 環境資訊（顯示在報告的 Environment 欄位）
# =========================
def pytest_configure(config):
    """
    在測試開始前，將環境資訊寫入 allure-results/environment.properties。
    這會顯示在 Allure 報告的 Overview → Environment 區塊，
    讓報告閱讀者一眼看出這次跑的是哪個環境、哪個瀏覽器版本。
    """
    # 只在有產出 allure-results 時才寫入（避免一般開發時產生垃圾檔案）
    allure_dir = config.getoption("--alluredir", default=None)
    if not allure_dir:
        return

    os.makedirs(allure_dir, exist_ok=True)
    env_file = os.path.join(allure_dir, "environment.properties")

    with open(env_file, "w") as f:
        f.write(f"Browser=Chromium\n")
        f.write(f"Base.URL=https://www.saucedemo.com\n")
        f.write(f"Python.Version={os.popen('python --version').read().strip()}\n")
        f.write(f"Framework=Playwright + Pytest\n")
        f.write(f"Environment=CI\n")