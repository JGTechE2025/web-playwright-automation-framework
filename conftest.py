"""
conftest.py

pytest 的全域設定檔，負責：
  1. 判斷執行環境（本機 / CI）
  2. 管理 Allure 報告的輸出路徑
  3. 提供瀏覽器 fixture 給所有測試使用
  4. 測試失敗時自動截圖並附加到 Allure 報告
"""

import os
import sys
import subprocess
from datetime import datetime

import allure
import pytest
from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────
# 模組層級初始化（import 時立即執行）
# ─────────────────────────────────────────────

def _get_timestamped_dirs() -> tuple[str, str]:
    """
    產生帶有時間戳記的 Allure 報告路徑（本機專用）。

    回傳：
      results_dir：allure-pytest 寫入原始 JSON 的路徑
      report_dir ：allure generate 產出 HTML 的路徑

    範例輸出：
      ("allure-runs/2025-07-10_14-30-00/results",
       "allure-runs/2025-07-10_14-30-00/report")

    設計決策：
      每次執行產生獨立資料夾，保留歷史報告，不互相覆蓋。
      CI 環境不使用此函式，固定寫入 allure-results/。
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = os.path.join("allure-runs", ts)
    return os.path.join(base, "results"), os.path.join(base, "report")


# 模組載入時就計算好路徑，確保同一次執行的 results / report 時間戳一致
_RESULTS_DIR, _REPORT_DIR = _get_timestamped_dirs()

# 判斷是否為 CI 環境
# GitHub Actions / CircleCI / Travis CI 等主流平台會自動注入 CI=true
# 使用環境變數而非 sys.argv 解析，原因：
#   sys.argv 的可用時機與格式因 pytest 版本而異（不穩定）
#   環境變數是跨語言、跨工具的業界標準契約
_IS_CI = os.environ.get("CI", "").lower() == "true"


# ─────────────────────────────────────────────
# pytest Hook 函式
# ─────────────────────────────────────────────

def pytest_addoption(parser):
    """
    註冊自訂 CLI 選項，讓使用者可以在執行 pytest 時傳入旗標。

    新增選項：
      --slow  ：啟用慢速模式（每個操作間隔 1000ms），方便人眼觀察畫面
      --headed：開啟瀏覽器視窗（預設為無頭模式 headless）

    使用範例：
      pytest --slow --headed   # 有視窗 + 慢速
      pytest                   # 無頭 + 正常速度（CI 預設）

    面試要點：
      addoption 只能在 conftest.py 裡宣告，不能在 test 檔案裡。
      這裡宣告的 option 之後可以在任何 fixture 或 hook 裡透過
      config.getoption("--slow") 取得值。
    """
    parser.addoption("--slow", action="store_true", default=False)
    parser.addoption("--headed", action="store_true", default=False)


def pytest_configure(config):
    """
    pytest 最早期的設定 hook，在任何測試收集或執行之前觸發。

    職責（CI 環境）：
      提前建立 allure-results/ 資料夾，確保 allure-pytest plugin
      在寫入報告資料時資料夾已存在（plugin 不會自動建立資料夾，
      資料夾不存在時會靜默失敗）。

    職責（本機環境）：
      不在這裡修改 alluredir，原因是此時 allure-pytest plugin
      可能尚未完成初始化，貿然修改 config.option 可能無效。
      本機路徑注入延遲到 pytest_sessionstart（更安全的時機）。

    面試要點：
      pytest hook 有嚴格的執行時序。pytest_configure 是最早期的 hook，
      適合做「環境準備」，不適合依賴其他 plugin 的狀態。
    """
    if _IS_CI:
        # CI：固定路徑，提前建立資料夾
        os.makedirs("allure-results", exist_ok=True)
        _write_environment_properties("allure-results")
    # 本機：路徑注入交給 pytest_sessionstart 處理，時序更安全


def pytest_sessionstart(session):
    """
    所有 plugin 的 configure 都完成後才觸發，是修改 plugin 設定的安全時機。

    職責（本機環境）：
      將 allure-pytest plugin 的輸出目錄（alluredir）
      指向帶有時間戳記的路徑，確保每次執行的報告互不干擾。

    為什麼不在 pytest_configure 做這件事？
      pytest_configure 執行時，allure-pytest plugin 可能還沒跑完自己的
      configure，此時修改 config.option.alluredir 可能被 plugin 覆蓋回去。
      pytest_sessionstart 保證所有 plugin 都已就緒，修改才會生效。

    面試要點：
      try/except AttributeError 是防禦性寫法——
      當使用者沒有安裝 allure-pytest 時，config.option 不會有 alluredir
      屬性，直接賦值會拋出 AttributeError。
      捕捉後忽略，讓測試可以在沒有 Allure 的環境下照常執行。
    """
    if _IS_CI:
        return  # CI 環境在 pytest_configure 已處理完畢，這裡不做任何事

    config = session.config
    os.makedirs(_RESULTS_DIR, exist_ok=True)

    try:
        # 將 allure-pytest plugin 的輸出路徑指向時間戳資料夾
        config.option.alluredir = _RESULTS_DIR
    except AttributeError:
        pass  # allure-pytest 未安裝時忽略，測試仍可正常執行

    _write_environment_properties(_RESULTS_DIR)


def pytest_sessionfinish(session, exitstatus):
    """
    所有測試執行完畢後觸發（本機專用）。

    職責：
      呼叫 allure generate 將原始 JSON 轉換為靜態 HTML 報告，
      並在終端機印出開啟指令，讓開發者一鍵查看。

    CI 環境為何跳過？
      CI 的報告產生由 GitHub Actions workflow 的獨立 step 負責，
      在這裡重複呼叫會造成路徑混亂。

    錯誤處理策略：
      FileNotFoundError → allure CLI 未安裝，給出安裝提示
      CalledProcessError → allure generate 執行失敗，印出詳細錯誤
      兩種情況都不讓測試結果因報告產生失敗而被污染。
    """
    if _IS_CI:
        return

    try:
        subprocess.run(
            ["allure", "generate", _RESULTS_DIR, "--clean", "-o", _REPORT_DIR],
            check=True,
        )
        print(f"\n✅ Allure report generated → allure open {_REPORT_DIR}")
    except FileNotFoundError:
        print("\n⚠️  allure CLI not found. 安裝方式：brew install allure")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ allure generate 執行失敗：{e}")


# ─────────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────────

def _write_environment_properties(allure_dir: str):
    """
    產生 Allure 報告首頁的環境資訊區塊（environment.properties）。

    這個檔案讓報告閱讀者一眼看出測試跑在什麼環境，
    在 Allure UI 的 Overview 頁面以 key-value 表格呈現。

    參數：
      allure_dir：environment.properties 要寫入的目錄路徑

    寫入內容範例：
      Browser=Chromium
      Base.URL=https://www.saucedemo.com
      Python.Version=Python 3.11.4
      Framework=Playwright + Pytest
      Environment=CI

    設計決策：
      使用 exist_ok=True 確保資料夾不存在時自動建立，
      避免因順序問題（此函式在 makedirs 之前被呼叫）拋出 FileNotFoundError。
    """
    os.makedirs(allure_dir, exist_ok=True)
    env_file = os.path.join(allure_dir, "environment.properties")
    with open(env_file, "w") as f:
        f.write("Browser=Chromium\n")
        f.write("Base.URL=https://www.saucedemo.com\n")
        f.write(f"Python.Version=Python {sys.version.split()[0]}\n")
        f.write("Framework=Playwright + Pytest\n")
        f.write(f"Environment={'CI' if _IS_CI else 'Local'}\n")


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def page(request):
    """
    提供 Playwright Page 物件給每個測試函式使用。

    生命週期：function（每個測試獨立一個瀏覽器實例，互不干擾）

    行為根據 CLI 選項動態調整：
      --slow  → slow_mo=1000，每個操作間隔 1 秒
      --headed → headless=False，開啟可視化視窗

    viewport 策略：
      有頭模式（--headed）：no_viewport=True，使用作業系統視窗實際大小
      無頭模式（預設）    ：固定 1920x1080，確保 CI 環境元素位置一致

    面試要點：
      為什麼用 fixture 而不是直接在 test 裡建立瀏覽器？
      fixture 確保 browser.close() 在測試結束後一定被執行（yield 的 teardown），
      避免測試失敗時殘留瀏覽器行程佔用記憶體。
    """
    slow = request.config.getoption("--slow")
    is_headless = not request.config.getoption("--headed")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_headless,
            args=["--start-maximized"] if not is_headless else [],
            slow_mo=1000 if slow else 0,
        )
        if is_headless:
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
        else:
            context = browser.new_context(no_viewport=True)

        page = context.new_page()
        yield page          # 把 page 交給測試函式使用
        browser.close()     # 測試結束（無論成功或失敗）後一定執行


@pytest.fixture(autouse=True)
def attach_screenshot_on_failure(request, page):
    """
    測試失敗時自動截圖並附加到 Allure 報告（全域自動掛載）。

    autouse=True 代表不需要在 test 函式參數裡宣告，所有測試自動套用。

    執行時序：
      yield 之前 → 什麼都不做（setup 階段）
      yield 之後 → 檢查測試是否失敗，失敗才截圖

    為什麼用 rep_call 而非直接判斷 exitstatus？
      rep_call 是 pytest 在 call 階段（實際測試執行）的結果物件，
      能精確區分「測試本身失敗」與「setup/teardown 失敗」。
      exitstatus 是整個 session 層級的，粒度太粗。

    錯誤處理：
      page.screenshot() 本身也可能失敗（例如瀏覽器已被關閉），
      用 try/except 確保截圖失敗不會覆蓋原本的測試失敗訊息。
    """
    yield   # 先讓測試跑完

    # 確認 call 階段的報告物件存在且測試失敗
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
            print(f"[Warning] 截圖失敗，原因：{e}")


# ─────────────────────────────────────────────
# Hook 實作（配合 attach_screenshot_on_failure）
# ─────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    攔截 pytest 的報告產生流程，把每個階段的結果存到 test item 上。

    為什麼需要這個 hook？
      attach_screenshot_on_failure fixture 在 yield 後需要知道
      「這個測試的 call 階段有沒有失敗」。
      但 fixture 的 teardown 時，pytest 尚未把結果放到 item 上，
      所以要透過這個 hook 提前把結果掛到 item 的屬性裡。

    tryfirst=True：確保這個 hook 在其他 plugin 的同名 hook 之前執行，
      讓 rep_call 屬性在 fixture teardown 時已可存取。

    hookwrapper=True：讓這個 hook 能「包住」原本的執行流程（yield 前後都能介入）。

    執行後效果：
      item.rep_setup → setup 階段結果
      item.rep_call  → 實際測試執行結果（fixture 截圖邏輯用這個）
      item.rep_teardown → teardown 階段結果
    """
    outcome = yield                         # 讓原本的 makereport 流程跑完
    rep = outcome.get_result()              # 取得該階段的報告物件
    setattr(item, f"rep_{rep.when}", rep)  # 掛到 item 上供 fixture 使用