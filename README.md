# 🧪 Web Automation Framework — Playwright + Pytest

> 模擬實務 QA 自動化測試流程的展示型專案，涵蓋 UI 測試、Flow 封裝與 Mock API 情境驗證。

---

## ✨ 專案特色

| 特色 | 說明 |
|------|------|
| 🏗️ Page Object Model | UI 操作與測試邏輯分離，易於維護 |
| 🔄 Flow 層封裝 | 將完整使用者流程（登入 → 購物 → 結帳）模組化 |
| 🎭 雙模式 Mock | Playwright Route Mock + FastAPI Mock Server 並存 |
| 🐢 Slow Mode | `--slow` 旗標讓測試以人眼可辨速度執行 |
| ⚡ 自動等待機制 | 利用 Playwright 內建等待，無需手動 sleep |
| 📦 fixture 管理 | `conftest.py` 統一管理瀏覽器生命週期 |
| 🚀 CI/CD 整合 | GitHub Actions 自動化流水線，含 Allure 報告部署至 GitHub Pages |

---

## 📂 專案架構

```
web-playwright-automation-framework/
├── .github/workflows/
│   └── main.yml        # CI/CD 流水線（測試 + Allure 部署）
├── pages/              # Page Object — UI 操作封裝（click / fill）
├── flows/              # Flow 層 — 使用者完整流程封裝
├── tests/              # 測試案例
├── utils/              # 工具模組（Mock API）
├── mock_server/        # FastAPI Mock Server
│   └── main.py
├── conftest.py         # pytest fixture（瀏覽器、slow mode、Allure）
├── requirements.txt
└── README.md
```

### 呼叫層級

```
Test → Flow → Page Object → Playwright
```

| 層級 | 職責 |
|------|------|
| **Test** | 執行 assert，驗證預期結果 |
| **Flow** | 組合多個 Page 操作成完整流程 |
| **Page Object** | 封裝單一頁面的 UI 互動 |
| **Playwright** | 底層自動化引擎 |

---

## ⚙️ 快速開始

```bash
# 1. 安裝 Python 套件
pip install -r requirements.txt

# 2. 安裝 Playwright 瀏覽器
playwright install

# 3. 執行所有測試（Playwright Route Mock，無需 server）
pytest

# 4. 以慢速模式執行（顯示操作畫面）
pytest --slow --headed

# 5. 執行特定標記
pytest -m smoke

# 6. 啟動 FastAPI Mock Server（選用）
uvicorn mock_server.main:app --reload
```

---

## 🧪 測試案例

### ✅ 成功流程（Flow 寫法）

```python
def test_checkout_success(page):
    flow = CheckoutFlow(page)
    flow.complete_checkout("standard_user", "secret_sauce")
    assert "checkout-complete" in page.url
```

### ❌ 失敗流程（傳統寫法，對比用）

```python
def test_checkout_fail(page):
    login.open()
    login.login("locked_out_user", "secret_sauce")
    # 手動逐步操作，展示 Flow 封裝的優勢
```

> 兩種寫法並存，用於說明 Flow 層如何提升測試可讀性與重用性。

---

## 🎭 Mock 架構

本專案支援兩種 mock 模式，可對應不同測試情境：

| 模式 | 架構 | 適用情境 |
|------|------|---------|
| 🟡 **Playwright Route Mock** | Browser → Playwright intercept → fake response | UI 測試、CI 快速驗證 |
| 🟢 **FastAPI Mock Server** | Browser → HTTP → FastAPI server → response | E2E 測試、API contract 驗證 |

### 🟡 Playwright Route Mock（CI 主要使用）

直接攔截瀏覽器請求，無需啟動任何 server：

```python
# utils/mock_payment.py
page.route("http://localhost/mock/payment", lambda route: route.fulfill(
    status=200,
    content_type="application/json",
    body='{"status": "success", "message": "payment approved"}'
))
```

### 🟢 FastAPI Mock Server

啟動後提供真實 HTTP 端點，驗證 API contract：

```bash
uvicorn mock_server.main:app --reload
# 預設位址：http://127.0.0.1:8000
```

---

## 🐢 Slow Mode

```bash
pytest --slow --headed
```

`conftest.py` 實作：每個操作間隔 1000ms，並開啟視窗方便觀察。

---

## 📊 Allure 測試報告

本專案整合 Allure 產出視覺化 HTML 報告，支援兩種模式：

### 本機報告（帶時間戳，保留歷史紀錄）

直接執行 `pytest` 即可，`conftest.py` 會自動：

1. 建立 `allure-runs/YYYY-MM-DD_HH-MM-SS/results/` 存放 raw JSON
2. 測試結束後自動呼叫 `allure generate`，產出 HTML 至 `allure-runs/YYYY-MM-DD_HH-MM-SS/report/`
3. 終端機顯示 `allure open <report_dir>` 指令，一鍵開啟報告

```
allure-runs/
├── 2025-07-10_14-30-00/
│   ├── results/    ← allure-pytest 產出的 raw JSON
│   └── report/     ← allure generate 產出的靜態 HTML
└── 2025-07-10_15-45-00/
    ├── results/
    └── report/
```

> `allure-runs/` 已加入 `.gitignore`，不會推送至 GitHub。

### CI 報告（GitHub Pages，永遠顯示最新一次結果）

每次 push 到 `main` 分支，GitHub Actions 自動執行：

```
pytest --alluredir=allure-results   →  產出 raw JSON
allure generate allure-results      →  產出靜態 HTML
peaceiris/actions-gh-pages          →  推送至 gh-pages branch
```

**GitHub Pages 設定（需手動設定一次）：**

1. 進入 GitHub repo → Settings → Pages
2. Source 選擇 `Deploy from a branch`
3. Branch 選擇 `gh-pages`，目錄選 `/ (root)`
4. 儲存後，推送一次 `main` 即可在以下網址看到報告：

```
https://<your-username>.github.io/<your-repo-name>/
```

---

## ⚡ Playwright vs Selenium

| 項目 | Playwright | Selenium |
|------|-----------|----------|
| 自動等待 | ✅ 內建 | ❌ 需手動 |
| 執行速度 | 快 | 較慢 |
| 穩定性 | 高 | 中 |
| API Mock | ✅ 原生支援 | ❌ 不支援 |
| 多瀏覽器 | ✅ Chromium / Firefox / WebKit | ✅ 多種 |

---

## 🚀 CI/CD 自動化流水線

### 技術棧

| 工具 | 用途 |
|------|------|
| GitHub Actions | CI/CD 執行環境 |
| Ubuntu Latest | 雲端測試環境 |
| Python 3.11 | 語言版本 |
| Chromium (Headless) | 瀏覽器引擎 |
| Allure CLI 2.27 | HTML 報告產生器 |
| peaceiris/actions-gh-pages | GitHub Pages 部署 |

### 流水線流程

```
push to main
    │
    ▼
1. Checkout code
2. Setup Python 3.11
3. Install pip dependencies
4. Install Playwright + Chromium
5. Install Allure CLI (Java)
    │
    ▼
6. Run Tests → allure-results/ (raw JSON) + report.xml
    │
    ▼
7. Generate Allure Report → allure-report/ (static HTML)
    │
    ▼
8. Upload Artifacts (report.xml + allure-results, 保留 7 天)
9. Deploy to GitHub Pages (gh-pages branch)
```

### 關鍵設計決策

**為什麼用 `|| true` 讓測試失敗時繼續執行？**
若測試失敗 GitHub Actions 預設會中止後續 step，導致報告無法產出。加上 `|| true` 讓流程繼續，才能在 Pages 上看到失敗詳情。

**為什麼 Deploy 步驟只在 `push` 時執行，PR 不執行？**
避免未經審查的 PR 程式碼覆蓋已部署的報告，保護 main 分支的報告完整性。

**為什麼需要 `permissions: contents: write`？**
GitHub Actions 預設 token 只有讀取權限。`peaceiris/actions-gh-pages` 需要寫入 `gh-pages` branch，必須明確宣告此權限。

---

## 🛠️ 技術挑戰與解決方案

### 1. YAML 語法精確度

**問題**：`Invalid workflow file`，CI 完全無法啟動。  
**根因**：YAML 對縮排極其敏感，多餘空格或錯誤的註解位置都會導致解析失敗。  
**解法**：統一使用兩格空格縮排，消除隱性格式錯誤。

---

### 2. Playwright 瀏覽器版本斷層

**問題**：`BrowserType.launch: Executable doesn't exist`。  
**根因**：`npx playwright install` 可能下載到與 Python 虛擬環境版本不匹配的瀏覽器。  
**解法**：改用 `python -m playwright install --with-deps chromium`，強制版本對齊並補齊 Ubuntu 系統依賴。

---

### 3. Headless 模式動態切換

**問題**：本地 `headless=False` 在 GitHub Actions 無螢幕環境下崩潰。  
**解法**：透過 `--headed` CLI option 動態判斷，本地看畫面、CI 自動無頭。

```python
is_headless = not request.config.getoption("--headed")
browser = playwright.chromium.launch(headless=is_headless)
```

---

### 4. GitHub Pages 顯示 README 而非 Allure 報告

**問題**：GitHub Pages 設定後顯示 README.md，看不到 Allure HTML。  
**根因**：Pages 指向 repo 根目錄，而非 Allure 靜態報告目錄。  
**解法**：使用 `peaceiris/actions-gh-pages` 將 `allure-report/` 推送至獨立的 `gh-pages` branch，Pages 指向該 branch 的根目錄即可顯示報告。

```yaml
- name: Deploy Allure Report to GitHub Pages
  uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./allure-report
    publish_branch: gh-pages
```

---

### 5. 雙層 Mock 架構整合

**問題**：Playwright Route Mock 無法驗證真實 HTTP contract（status code 語意、response schema）。  
**解法**：Route Mock 跑 CI 快速驗證，FastAPI Server Mock 跑 integration 環境驗證，透過 `utils/mock_payment.py` 統一介面，測試只需換一行即可切換。

---

### 6. fetch 回傳 HTML 導致 JSON 解析失敗

**問題**：`SyntaxError: Unexpected token '<'`，`response.json()` 崩潰。  
**根因**：相對路徑 `/mock/payment` 在 saucedemo.com context 被解析為 `https://www.saucedemo.com/mock/payment`，伺服器回傳 HTML 404。  
**解法**：改用絕對路徑 `http://localhost/mock/payment`，Playwright Route Mock 只需 pattern 匹配即可攔截，URL 不需真實存在。

```python
# 修正前（錯誤）
fetch('/mock/payment')

# 修正後（正確）
fetch('http://localhost/mock/payment')
```

---

### 7. conftest.py 的本機優化邏輯干涉 CI 的 alluredir 設定

**問題**：CI 顯示「No files were found with the provided path: allure-results/」，
GitHub Pages 始終顯示 README 而非 Allure 報告。

**根因**：`conftest.py` 的 `pytest_configure` hook 透過讀取 allure-pytest 
plugin 的內部 option `allure_report_dir` 來判斷是否為本機環境。
但該 option 在某些版本的預設值為空字串而非 `None`，
導致 `if not current_dir` 判斷為 `True`，
即使 CI 明確傳入 `--alluredir=allure-results`，
本機時間戳路徑仍會將其覆蓋，
使 `allure-results/` 資料夾從未在 CI 環境中建立。

**解法**：改用 `sys.argv` 直接偵測使用者是否傳入了 `--alluredir` 參數，
不再依賴 plugin 內部 option 的命名與預設值行為，
徹底避免本機邏輯影響 CI 環境。

**教訓**：hook 函式應只修改自己「確定沒有值」的設定，
並用最外層可觀察的介面（argv）判斷執行環境，
而非依賴框架內部 option 的預設值行為。

---

### 8. CI 環境判斷邏輯導致 allure-results 靜默未建立

**問題**：CI log 顯示 `allure-results NOT found`，
`pytest --alluredir=allure-results` 執行後資料夾完全不存在。

**根因**：`conftest.py` 以 `sys.argv` 解析是否為 CI 環境，
但這種做法對 argv 的解析時序有隱性依賴；
更關鍵的是，`allure-pytest` plugin 在目標資料夾不存在時
可能靜默失敗，不拋出任何錯誤。

**解法**：
1. 改用 `os.environ.get("CI") == "true"` 判斷 CI 環境——
   GitHub Actions 會自動注入此變數，這是跨平台的業界標準。
2. 在 `pytest_configure` 階段提前呼叫 `os.makedirs("allure-results", exist_ok=True)`，
   確保資料夾在 plugin 嘗試寫入之前就已存在。

**教訓**：環境判斷應依賴平台注入的標準環境變數，
而非解析 CLI argv——後者的可用時機與格式因框架版本而異，
是不穩定的實作細節。

---

### 9. --headed CLI option 與 pytest-playwright 內建選項衝突

**問題**：CI 執行時 pytest 在啟動階段即崩潰，
`argparse.ArgumentError: conflicting option string: --headed`，
導致零測試執行、allure-results 為空、報告部署失敗。

**根因**：`pytest-playwright` 插件本身內建了 `--headed` option，
而 `conftest.py` 的 `pytest_addoption` 重複宣告了同名 option，
pytest 的 argparse 層不允許重複，因此在 conftest 載入時直接拋出例外。

**解法**：移除 `conftest.py` 中重複的 `--headed` 宣告，
直接使用 `pytest-playwright` 提供的版本。
`request.config.getoption("--headed")` 的呼叫方式完全不變。

**教訓**：引入 pytest 插件前應確認其內建 CLI option 清單，
避免在 `conftest.py` 重複宣告造成衝突。
`pytest-playwright` 的內建 option 包含 `--headed`、`--browser`、`--slowmo` 等。

---

## 🗺️ 未來規劃

- [x] CI/CD（GitHub Actions）整合
- [x] Allure Report + GitHub Pages 部署
- [x] 本機測試報告按日期時間戳分類管理
- [x] 全面串接 FastAPI Mock Server
- [x] 建立獨立 API test layer
- [ ] Logging 模組整合
- [ ] `.env` 環境變數管理（區分測試與正式環境）
- [ ] API Response 驗證（`wait_for_response` 強化非同步測試）
- [ ] Data-Driven Testing（pytest parametrize / 外部 CSV）

---

## 📣 專案說明

本專案為**學習與面試展示用途**，以 [Sauce Demo](https://www.saucedemo.com/) 為測試目標，模擬實務 QA 自動化測試的完整流程與架構設計。