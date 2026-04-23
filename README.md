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
| 🚀 CI/CD 整合 | 導入 GitHub Actions 實現自動化流水線，支援環境相依性檢核與測試報告產出 |

---

## 📂 專案架構

```
web-playwright-automation-framework/
├── pages/              # Page Object — UI 操作封裝（click / fill）
├── flows/              # Flow 層 — 使用者完整流程封裝
├── tests/              # 測試案例
├── utils/              # 工具模組（Mock API）
├── mock_server/        # FastAPI Mock Server
│   └── main.py
├── conftest.py         # pytest fixture（瀏覽器、slow mode）
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
    ...
```

> 兩種寫法並存，用於說明 Flow 層如何提升測試可讀性與重用性。

---

## 🎭 Mock 架構

本專案支援兩種 mock 模式，可對應不同測試情境：

| 模式 | 架構 | 適用情境 |
|------|------|---------|
| 🟡 **Playwright Route Mock** | Browser → Playwright intercept → fake response | UI 測試、快速驗證 |
| 🟢 **FastAPI Mock Server** | Browser → HTTP → FastAPI server → response | E2E 測試、API contract 驗證 |

---

### 🟡 Playwright Route Mock（目前主要使用）

直接攔截瀏覽器請求，無需啟動任何 server：

```python
# 模擬付款成功
page.route("**/mock/payment", lambda route: route.fulfill(
    status=200,
    content_type="application/json",
    body='{"status": "success", "message": "payment approved"}'
))

# 模擬付款失敗
page.route("**/mock/payment", lambda route: route.fulfill(
    status=400,
    content_type="application/json",
    body='{"status": "failed", "message": "payment rejected"}'
))
```

**支援情境：**
- ✅ Payment 成功 → 驗證訂單完成頁面
- ❌ Payment 失敗 → 驗證錯誤提示訊息

---

### 🟢 FastAPI Mock Server（已建立，尚未全面串接）

模擬真實 backend 行為，適合驗證 API contract：

**啟動 server：**

```bash
uvicorn mock_server.main:app --reload
# 預設位址：http://127.0.0.1:8000
```

**Payment API：**

```
POST /mock/payment
```

```json
// Response — 成功
{ "status": "success", "message": "payment approved" }

// Response — 失敗
{ "status": "failed", "message": "payment rejected" }
```

**檔案位置：** `mock_server/main.py`

---

## 🐢 Slow Mode

以慢速執行測試，方便展示或 debug：

```bash
pytest --slow
```

`conftest.py` 實作：

```python
browser = p.chromium.launch(
    headless=False,
    slow_mo=500  # 每個操作間隔 500ms
)
```

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
pytest --slow

# 5. 執行特定標記
pytest -m smoke

# 6. 啟動 FastAPI Mock Server（選用）
uvicorn mock_server.main:app --reload
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

## ⚠️ 常見問題

**`TimeoutError` 頁面未載入？**

```python
# ✅ 等待頁面狀態變化，而非固定 sleep
page.wait_for_url("**/inventory.html")
```

**測試速度太快看不清楚？**

```bash
pytest --slow
```

---

## 🚀 CI/CD 自動化測試流水線 (Playwright)

本專案已導入 **GitHub Actions** 實作完整的持續整合 (CI) 流程，確保代碼品質與測試穩定性，並針對 **Playwright** 框架進行雲端環境最佳化。

---

### 🛠️ 技術棧與環境配置
* **CI 工具**: GitHub Actions
* **執行環境**: Ubuntu Latest (Linux)
* **語言版本**: Python 3.11
* **瀏覽器引擎**: Chromium, Firefox, WebKit (**Headless Mode**)

---

### 📋 流水線流程說明

1. **代碼偵測 (Trigger)**：監控 `main` 分支的 `push` 或 `pull request` 事件，即自動觸發。
2. **環境配置 (Setup)**：於雲端自動建立獨立的 Python 3.11 虛擬環境。
3. **依賴安裝 (Dependencies)**：
    * 自動根據 `requirements.txt` 安裝專案所需 Python 套件。
    * 執行 `playwright install --with-deps` 初始化雲端瀏覽器核心及必要的 Linux 系統相依函式庫。
4. **自動化測試 (Test)**：執行測試腳本並產生詳細執行日誌 (Log)，確保功能未受損壞。
5. **產出物保存 (Artifacts)**：無論測試成功或失敗，系統皆會自動保存測試產出（如 Log、報告、截圖等），保留期為 7 天。

---

### 📈 實踐意義

* **自動化門神**：減少人為疏失，確保進入倉庫的代碼皆通過雲端乾淨環境的驗證。
* **快速回饋**：透過雲端執行日誌，能在第一時間發現環境相容性或程式邏輯問題。
* **跨平台驗證**：實作測試腳本在無 GUI (Headless) 環境下的穩定執行能力，解決「本機跑得過，雲端跑不動」的常見問題。

---

### 🛠️ 專案初始化紀錄 (Internal Development Notes)

為確保開發流程可追溯，以下紀錄本專案於 IDE 環境中配置 CI/CD 的關鍵步驟：

1. **目錄結構規範**：於專案根目錄建立 `.github/workflows/` 資料夾，並配置 `main.yml` 定義自動化邏輯。
2. **Node.js 版本控制**：全域設定 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` 環境變數，確保流水線符合最新安全與執行標準。
3. **相依性同步**：透過 `pip freeze > requirements.txt` 確保本機與雲端執行環境的 Python Library 版本對齊。
4. **CI 穩定性驗證**：初期透過 Shell 指令 (echo) 驗證虛擬機軌道佈署成功後，再導入真實自動化腳本。

---

## 🛠️ 技術挑戰與 CI/CD 踩坑紀錄 (Troubleshooting)

在佈署 GitHub Actions 自動化流程時，針對 Playwright 環境遭遇了以下關鍵挑戰並成功修復：

### 1. YAML 語法精確度 (YAML Syntax)
* **問題描述**：初期出現 `Invalid workflow file` 報錯，導致 CI 完全無法啟動。
* **原因分析**：YAML 檔案對**縮排（Indentation）**與**空格**極其敏感，註解位置不對或多餘的空格都會導致解析失敗。
* **解決方案**：重新對齊 `run: |` 下方的指令，確保所有 shell 指令與註解層級一致，維持標準的兩格空格縮排。

### 2. Playwright 瀏覽器版本斷層 (Executable Doesn't Exist)
* **問題描述**：CI 執行時噴出 `BrowserType.launch: Executable doesn't exist`。雖然執行了安裝指令，但 Python 套件仍找不到瀏覽器執行檔。
* **解決方案**：
    * **核心原因**：使用 `npx playwright install` 有時會下載到與 Python 虛擬環境中 `playwright` 套件版本不匹配的瀏覽器。
    * **修正指令**：改用 `python -m playwright install --with-deps chromium`。
    * **關鍵點**：透過 `python -m` 指令能強制對齊「當前 Python 套件」與「瀏覽器執行檔」的版本，並透過 `--with-deps` 補齊 Ubuntu Linux 系統所需的相依函式庫（如 `.so` 檔），徹底解決執行檔遺失問題。

### 3. Headless 模式動態切換 (Environment Adaptation)
* **問題描述**：本地開發為了除錯慣用 `headless=False`（有頭模式），但在 GitHub Actions（無螢幕伺服器環境）會導致系統因找不到顯示設備而崩潰。
* **解決方案**：重構 `conftest.py` 中的 `page` fixture，利用 `pytest` 的 `request.config` 實作動態判斷邏輯：
    ```python
    # 判斷指令是否含有 --headed 參數，若無則預設啟動無頭模式
    is_headless = not request.config.getoption("--headed")
    browser = playwright.chromium.launch(
        headless=is_headless,
        slow_mo=2000 if slow else 0
    )
    ```
* **效果**：達成「本地開發看畫面、雲端 CI 自動無頭」的靈活適配，兼顧開發直觀性與 CI 穩定性。

### 4. 測試報告可視化 (Artifacts Reporting)
* **問題描述**：預設產出的 `report.xml` 為 XML 原始碼格式，直接開啟時缺乏可讀性。
* **優化方案**：已配置 GitHub Artifacts 自動歸檔功能，未來將導入 `pytest-html` 產出視覺化 HTML 報告，提升測試結果的透明度與分析效率。

---

## 🗺️ 未來規劃

- [x] CI/CD（GitHub Actions）整合：實作 Playwright 雲端環境自動化部署
- [ ] 全面串接 FastAPI Mock Server，取代 Playwright Route Mock
- [ ] 建立獨立 API test layer（驗證 backend 行為）
- [ ] Allure Report 測試報告產出與 GitHub Pages 託管
- [ ] Logging 模組整合（增加 Log 紀錄與產出）
- [ ] `.env` 環境變數管理（區分測試與正式環境）
- [ ] API Response 驗證（使用 `wait_for_response` 強化非同步測試）

---

## 📣 專案說明

本專案為**學習與面試展示用途**，以 [Sauce Demo](https://www.saucedemo.com/) 為測試目標，模擬實務 QA 自動化測試的完整流程與架構設計。
