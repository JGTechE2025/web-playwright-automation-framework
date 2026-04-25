# conftest.py（新增 / 修改的段落，其餘保持不變）

import os
from datetime import datetime
import allure
import pytest
from playwright.sync_api import sync_playwright


# =========================
# 時間戳報告目錄（新增）
# =========================
def _get_timestamped_dirs() -> tuple[str, str]:
    """
    產生帶時間戳的 results / report 目錄路徑。

    格式範例：
      allure-runs/2025-07-10_14-30-55/results/
      allure-runs/2025-07-10_14-30-55/report/

    設計決策：
      - 用同一個時間戳讓 results 和 report 放在同一個資料夾，方便對照。
      - 頂層統一用 allure-runs/ 集中管理，不污染專案根目錄。
      - 時間戳精確到秒，避免短時間內連跑兩次互蓋。
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = os.path.join("allure-runs", ts)
    results_dir = os.path.join(base, "results")
    report_dir = os.path.join(base, "report")
    return results_dir, report_dir


# 模組層級產生一次，讓所有 hook 共用同一個時間戳
_RESULTS_DIR, _REPORT_DIR = _get_timestamped_dirs()


# =========================
# CLI options
# =========================
def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="run tests with slow motion (500ms between actions)"
    )


# =========================
# pytest_configure：注入 alluredir + 寫環境資訊
# =========================
def pytest_configure(config):
    """
    關鍵設計：
      若使用者沒有手動指定 --alluredir，自動注入時間戳路徑。
      若有手動指定（例如 CI 環境），尊重使用者設定不覆蓋。

    面試要點：
      為什麼不用 pytest.ini 寫死 --alluredir？
      因為寫死路徑每次都蓋掉舊資料。動態注入才能保留每次的歷史紀錄。
    """
    # 只在沒有手動指定 --alluredir 時才注入（讓 CI 的設定不被干擾）
    if not config.option.__dict__.get("allure_report_dir"):
        config.option.allure_report_dir = _RESULTS_DIR

    allure_dir = config.option.allure_report_dir
    os.makedirs(allure_dir, exist_ok=True)

    env_file = os.path.join(allure_dir, "environment.properties")
    with open(env_file, "w") as f:
        f.write("Browser=Chromium\n")
        f.write("Base.URL=https://www.saucedemo.com\n")
        f.write(f"Python.Version={os.popen('python --version').read().strip()}\n")
        f.write("Framework=Playwright + Pytest\n")
        f.write("Environment=Local\n")


# =========================
# pytest_sessionfinish：自動產生 HTML 報告（新增）
# =========================
def pytest_sessionfinish(session, exitstatus):
    """
    所有測試跑完後，自動執行 allure generate，
    把 results（raw JSON）→ report（靜態 HTML）。

    設計決策：
      放在 sessionfinish 而非用 subprocess 包在 Makefile 裡，
      原因是讓「跑測試」這一個動作就能完成所有事，
      不需要記額外指令，降低使用者心智負擔。

    面試補充：
      exitstatus != 0 代表有測試失敗，但我們仍然要產報告（才能看失敗原因），
      所以不做 exitstatus 判斷，無條件產出。
    """
    import subprocess
    try:
        subprocess.run(
            ["allure", "generate", _RESULTS_DIR, "--clean", "-o", _REPORT_DIR],
            check=True,
        )
        print(f"\n✅ Allure report generated → {_REPORT_DIR}")
        print(f"   Run: allure open {_REPORT_DIR}")
    except FileNotFoundError:
        print("\n⚠️  allure CLI not found. Install: brew install allure")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ allure generate failed: {e}")


# =========================
# Browser fixture
# =========================
@pytest.fixture
def page(request):
    slow = request.config.getoption("--slow")
    is_headless = not request.config.getoption("--headed")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_headless,
            slow_mo=1000 if slow else 0
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        yield page
        browser.close()


# =========================
# Allure 自動截圖 fixture
# =========================
@pytest.fixture(autouse=True)
def attach_screenshot_on_failure(request, page):
    yield
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        try:
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name=f"FAILED - {request.node.name}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as e:
            print(f"[Warning] Screenshot failed: {e}")


# =========================
# pytest hook：追蹤 phase 結果
# =========================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)