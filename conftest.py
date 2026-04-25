"""
conftest.py
"""

import os
import sys
import subprocess
from datetime import datetime

import allure
import pytest
from playwright.sync_api import sync_playwright


def _get_timestamped_dirs() -> tuple[str, str]:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = os.path.join("allure-runs", ts)
    return os.path.join(base, "results"), os.path.join(base, "report")


_RESULTS_DIR, _REPORT_DIR = _get_timestamped_dirs()

_IS_CI = any("--alluredir" in arg for arg in sys.argv)


def pytest_addoption(parser):
    parser.addoption("--slow", action="store_true", default=False)
    parser.addoption("--headed", action="store_true", default=False)


def pytest_configure(config):
    """
    只負責環境偵測。
    路徑注入移到 pytest_sessionstart，確保 allure-pytest plugin 已完成初始化。
    """
    if _IS_CI:
        _write_environment_properties("allure-results")
    # 本機路徑注入：不在這裡做，避免與 allure plugin 的 configure 順序衝突


def pytest_sessionstart(session):
    """
    所有 plugin configure 完成後才執行，此時修改 alluredir 才安全。

    面試要點：
      pytest hook 有明確的執行時序。pytest_configure 是最早期的 hook，
      plugin 可能還未完全就緒。pytest_sessionstart 則保證所有 plugin
      都已完成初始化，是修改 plugin 設定的安全時機。
    """
    if _IS_CI:
        return

    # 本機：把 allure plugin 的輸出目錄指向時間戳路徑
    config = session.config
    os.makedirs(_RESULTS_DIR, exist_ok=True)

    # allure-pytest 用 alluredir 這個 option name
    try:
        config.option.alluredir = _RESULTS_DIR
    except AttributeError:
        pass  # allure plugin 未載入時忽略

    _write_environment_properties(_RESULTS_DIR)


def _write_environment_properties(allure_dir: str):
    os.makedirs(allure_dir, exist_ok=True)
    env_file = os.path.join(allure_dir, "environment.properties")
    with open(env_file, "w") as f:
        f.write("Browser=Chromium\n")
        f.write("Base.URL=https://www.saucedemo.com\n")
        f.write(f"Python.Version=Python {sys.version.split()[0]}\n")
        f.write("Framework=Playwright + Pytest\n")
        f.write(f"Environment={'CI' if _IS_CI else 'Local'}\n")


def pytest_sessionfinish(session, exitstatus):
    if _IS_CI:
        return
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
        if is_headless:
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
        else:
            context = browser.new_context(no_viewport=True)

        page = context.new_page()
        yield page
        browser.close()


@pytest.fixture(autouse=True)
def attach_screenshot_on_failure(request, page):
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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)