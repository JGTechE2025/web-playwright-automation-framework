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

## 🚀 CI/CD 整合實作 (Continuous Integration)

本專案已導入 **GitHub Actions** 實作持續整合流程，確保代碼品質與測試穩定性。

### 🛠️ 技術棧與環境
- **CI 工具**: GitHub Actions
- **執行環境**: Ubuntu Latest (Linux)
- **語言版本**: Python 3.11

### 📋 流水線流程說明
1. **代碼偵測**: 只要有新的代碼 `push` 或 `pull request` 至 `main` 分支，即自動觸發。
2. **環境配置**: 自動建立 Python 3.11 虛擬環境。
3. **依賴安裝**: 自動根據 `requirements.txt` 安裝專案所需套件。
4. **自動化測試**: 執行測試腳本並產生執行日誌 (Log)，確保功能未受損壞。

### 📈 實踐意義
- **自動化門神**: 減少人為疏失，確保進入倉庫的代碼皆通過環境驗證。
- **快速回饋**: 透過雲端執行日誌，能在第一時間發現環境相容性或程式邏輯問題。
- **無頭模式 (Headless)**: 實作測試腳本在無 GUI 環境下的穩定執行能力。

---

## 🗺️ 未來規劃

- [ ] 全面串接 FastAPI Mock Server，取代 Playwright Route Mock
- [ ] 建立獨立 API test layer（驗證 backend 行為）
- [ ] Allure Report 測試報告
- [ ] Logging 模組整合
- [ ] `.env` 環境變數管理
- [ ] CI/CD（GitHub Actions）
- [ ] API Response 驗證（`wait_for_response`）

---

## 📣 專案說明

本專案為**學習與面試展示用途**，以 [Sauce Demo](https://www.saucedemo.com/) 為測試目標，模擬實務 QA 自動化測試的完整流程與架構設計。
