"""
conftest.py

pytest 的全域設定檔，負責：
  1. 自動管理 Allure 報告的輸出路徑與歷史紀錄
  2. 提供瀏覽器 fixture (Playwright)
  3. 測試失敗時自動截圖並附加到 Allure 報告
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime
import allure
import pytest
from playwright.sync_api import sync_playwright

# ─────────────────────────────────────────────
# 全域變數與路徑管理
# ─────────────────────────────────────────────

# 判斷是否為 CI 環境 (如 GitHub Actions)
_IS_CI = os.environ.get("CI", "").lower() == "true"

def _get_timestamped_dirs():
    """產生帶有時間戳記的 Allure 路徑（本機開發專用）"""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = os.path.join("allure-runs", ts)
    return os.path.join(base, "results"), os.path.join(base, "report")

# ─────────────────────────────────────────────
# pytest Hooks (報告管理)
# ─────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    """
    所有測試執行完畢後。
    職責：
      1. 將 allure-results 的原始資料搬移到帶有時間戳的目錄（保留歷史）
      2. 產生 HTML 靜態報告
    """
    if _IS_CI:
        return

    # 取得 pytest.ini 或 CLI 指定的 alluredir (預設為 allure-results)
    current_results = getattr(session.config.option, "alluredir", "allure-results")
    
    if not current_results or not os.path.exists(current_results):
        return

    # 檢查是否有實際結果產生
    has_results = any(f.endswith(".json") for f in os.listdir(current_results))
    if not has_results:
        return

    # 建立本次執行的專屬目錄
    target_results, target_report = _get_timestamped_dirs()
    os.makedirs(target_results, exist_ok=True)

    # 將結果從暫存區搬移到歷史區
    for filename in os.listdir(current_results):
        shutil.move(os.path.join(current_results, filename), target_results)

    # 【修正】搬移完成後，刪除已空掉的暫存資料夾
    try:
        shutil.rmtree(current_results)
    except Exception:
        pass

    # 產生 HTML 報告
    abs_results = os.path.abspath(target_results)
    abs_report = os.path.abspath(target_report)

    try:
        subprocess.run(
            ["allure", "generate", abs_results, "--clean", "-o", abs_report],
            check=True,
            shell=True
        )
        print(f"\n" + "="*60)
        print(f"✅ Allure 測試結果已存檔：{abs_results}")
        print(f"📊 HTML 報告已產生：{abs_report}")
        print(f"💡 請執行以下指令查看報告：")
        print(f"   allure open \"{abs_report}\"")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ Allure 報告產生失敗: {e}")

# ─────────────────────────────────────────────
# Fixtures & 其他設定
# ─────────────────────────────────────────────

def pytest_addoption(parser):
    """註冊自定義 CLI 選項"""
    parser.addoption("--slow", action="store_true", default=False, help="每個操作間隔 1 秒")


@pytest.fixture
def page(request):
    """建立 Playwright 瀏覽器分頁

    設計決策：
      - CI 環境（沒有螢幕）強制使用 headless，避免 XServer missing 錯誤
      - 本機可透過 --headed 開啟視窗，方便 debug
      - --slow 讓每步操作延遲 1 秒，人眼可追蹤流程
    """
    slow = request.config.getoption("--slow")

    # pytest-playwright 的 --headed option 在 CI 可能被誤傳，
    # 加上 _IS_CI 雙重保護，確保 CI 永遠是 headless
    is_headed = getattr(request.config.option, "headed", False) and not _IS_CI

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not is_headed,
            slow_mo=1000 if slow else 0,
            args=["--start-maximized"] if is_headed else []
        )
        context = browser.new_context(no_viewport=is_headed)
        page = context.new_page()
        yield page
        browser.close()

@pytest.fixture(autouse=True)
def attach_screenshot_on_failure(request, page):
    """失敗時自動截圖"""
    yield
    item = request.node
    if hasattr(item, "rep_call") and item.rep_call.failed:
        try:
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name=f"FAILED_{item.name}",
                attachment_type=allure.attachment_type.PNG
            )
        except Exception:
            pass

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """獲取測試結果狀態"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
