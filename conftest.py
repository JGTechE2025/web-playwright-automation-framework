"""
conftest.py

職責：
  - 管理 Playwright 瀏覽器生命週期（page fixture）
  - 動態注入 Allure 時間戳目錄（本機用）
  - 失敗時自動截圖並附加至 Allure 報告
  - 測試結束後自動呼叫 allure generate（本機用）

設計決策：
  CI 環境透過 pytest --alluredir=allure-results 手動指定輸出目錄，
  本機若未指定則自動注入帶時間戳的路徑，保留每次的歷史紀錄。
"""

import os
import sys
import subprocess
from datetime import datetime

import allure
import pytest
from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────
# 時間戳報告目錄（本機用）
# ─────────────────────────────────────────────
def _get_timestamped_dirs() -> tuple[str, str]:
    """
    產生帶時間戳的 results / report 目錄路徑。

    格式範例：
      allure-runs/2025-07-10_14-30-55/results/
      allure-runs/2025-07-10_14-30-55/report/

    設計決策：
      - 同一時間戳讓 results 和 report 放在同一資料夾，方便對照。
      - 頂層統一用 allure-runs/ 集中管理，不污染專案根目錄。
      - 精確到秒，避免短時間連跑兩次互蓋。
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = os.path.join("allure-runs", ts)
    return os.path.join(base, "results"), os.path.join(base, "report")


# 模組層級產生一次，讓所有 hook 共用同一個時間戳
_RESULTS_DIR, _REPORT_DIR = _get_timestamped_dirs()


# ─────────────────────────────────────────────
# CLI options
# ─────────────────────────────────────────────
def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run tests with slow motion (1000ms between actions)",
    )
    # 修正：--headed 必須在這裡宣告，否則 getoption 會拋出 ValueError
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed (visible browser) mode",
    )


# ─────────────────────────────────────────────
# pytest_configure：注入 alluredir
# ─────────────────────────────────────────────
def pytest_configure(config):
    """
    本機模式：動態注入時間戳 alluredir。
    CI 模式：完全不干涉，由 --alluredir=allure-results 控制。
    """
    is_ci_explicit = any("--alluredir" in arg for arg in sys.argv)
    if is_ci_explicit:
        # CI 環境：只做環境資訊寫入，路徑完全由 CLI 參數決定
        _write_environment_properties("allure-results")
        return

    # 本機環境：注入時間戳路徑
    # allure-pytest 內部用的 key 是 "alluredir"，不是 "allure_report_dir"
    config.option.alluredir = _RESULTS_DIR
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    _write_environment_properties(_RESULTS_DIR)


# ─────────────────────────────────────────────
# 將環境資訊寫入 Allure 的 environment.properties
# ─────────────────────────────────────────────
def _write_environment_properties(allure_dir: str):
    os.makedirs(allure_dir, exist_ok=True)
    env_file = os.path.join(allure_dir, "environment.properties")
    with open(env_file, "w") as f:
        f.write("Browser=Chromium\n")
        f.write("Base.URL=https://www.saucedemo.com\n")
        f.write(f"Python.Version=Python {sys.version.split()[0]}\n")
        f.write("Framework=Playwright + Pytest\n")
        f.write("Environment=Local\n")


def pytest_sessionfinish(session, exitstatus):
    is_ci_explicit = any("--alluredir" in arg for arg in sys.argv)
    if is_ci_explicit:
        return

    # 本機才自動產報告
    try:
        subprocess.run(
            ["allure", "generate", _RESULTS_DIR, "--clean", "-o", _REPORT_DIR],
            check=True,
        )
        print(f"\n✅ Allure report → allure open {_REPORT_DIR}")
    except FileNotFoundError:
        print("\n⚠️  allure CLI not found. Install: brew install allure")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ allure generate failed: {e}")


# ─────────────────────────────────────────────
# Browser fixture
# ─────────────────────────────────────────────
@pytest.fixture
def page(request):
    slow = request.config.getoption("--slow")
    is_headless = not request.config.getoption("--headed")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_headless,
            args=["--start-maximized"] if not is_headless else [],
            slow_mo=1000 if slow else 0,
        )

        # headed 模式：no_viewport=True 讓視窗跟隨最大化
        # headless 模式：寫死 1920x1080，避免 CI 環境元素跑版
        if is_headless:
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
        else:
            context = browser.new_context(no_viewport=True)

        page = context.new_page()
        yield page
        browser.close()


# ─────────────────────────────────────────────
# Allure 自動截圖 fixture
# ─────────────────────────────────────────────
@pytest.fixture(autouse=True)
def attach_screenshot_on_failure(request, page):
    """
    測試失敗時自動截圖並附加至 Allure 報告。
    autouse=True 讓所有測試自動套用，無需手動標記。
    """
    yield
    failed = (
        request.node.rep_call.failed
        if hasattr(request.node, "rep_call")
        else False
    )
    if failed:
        try:
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name=f"FAILED - {request.node.name}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as e:
            print(f"[Warning] Screenshot capture failed: {e}")


# ─────────────────────────────────────────────
# pytest hook：追蹤各 phase 結果（給截圖 fixture 用）
# ─────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)