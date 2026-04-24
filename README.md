## 📊 Allure Report 測試報告（GitHub Pages 託管）

本專案已整合 **Allure Report**，每次 Push 到 `main` 分支後，CI 會自動產出視覺化測試報告並部署至 GitHub Pages。

---

### 🔗 線上報告

> **[查看最新測試報告 →](https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/)**

---

### ✨ 報告特色

| 功能 | 說明 |
|------|------|
| 📈 趨勢圖 | 追蹤歷次執行的通過率變化 |
| 🧩 步驟拆解 | 每個 `with allure.step()` 都會在報告中展開 |
| 📸 失敗截圖 | 測試 FAILED 時自動截圖並嵌入報告 |
| 🏷️ 分類標籤 | Epic / Feature / Story 三層結構，對應業務模組 |
| 🌍 環境資訊 | 顯示 Browser、Python 版本、測試環境 |
| 📎 附件 | API Response JSON 直接嵌入，無需另開檔案 |

---

### 🛠️ 本地產出報告

```bash
# 1. 執行測試，產出原始資料
pytest --alluredir=allure-results -v

# 2. 安裝 Allure CLI（macOS）
brew install allure

# 2. 安裝 Allure CLI（Windows - Scoop）
scoop install allure

# 3. 產出 HTML 報告並自動開啟瀏覽器
allure serve allure-results

# 或：先 generate 再手動開啟
allure generate allure-results --clean -o allure-report
allure open allure-report
```

---

### ⚙️ GitHub Pages 首次啟用步驟

1. 前往 `Settings` → `Pages`
2. Source 選擇 **GitHub Actions**
3. Push 一次到 `main` 分支，等待 CI 執行完畢
4. 報告網址格式：`https://<username>.github.io/<repo-name>/`

> **注意**：`main.yml` 已設定 `permissions: pages: write`，無需額外設定 token。

---

### 🧱 Allure 裝飾器架構

```python
@allure.epic("電商平台自動化測試")      # 最高層：產品模組
@allure.feature("結帳流程")            # 功能模組
class TestCheckout:

    @allure.story("支付成功 - E2E")    # 使用者故事
    @allure.severity(allure.severity_level.BLOCKER)
    def test_checkout_success(self, page):
        with allure.step("設定支付成功 Mock"):
            mock_payment_success(page)

        with allure.step("斷言 URL 包含 checkout-complete"):
            assert "checkout-complete" in page.url

        # 附加截圖至報告
        allure.attach(
            page.screenshot(),
            name="完成頁面截圖",
            attachment_type=allure.attachment_type.PNG,
        )
```

---

### 🚀 CI 流水線（Allure 段落）

```
Push to main
    ↓
pytest --alluredir=allure-results   ← 產出 JSON raw data
    ↓
allure generate allure-results      ← JSON → 靜態 HTML
    ↓
upload-pages-artifact               ← 打包 HTML
    ↓
deploy-pages                        ← 部署到 GitHub Pages
    ↓
https://you.github.io/repo/         ← 公開報告網址
```

---

### 🛠️ 技術挑戰與解決方案 (Allure + GitHub Pages)

#### 挑戰 7：Allure 報告部署至 GitHub Pages

**問題描述**：GitHub Pages 官方要求部署必須使用獨立 job，且需要特定 `permissions` 設定，否則 deploy 步驟回傳 `403 Permission denied`。

**根因分析**：
- `upload-pages-artifact` 和 `deploy-pages` 必須在 build job 中分開，否則 Pages 無法正確識別 artifact。
- 缺少 `permissions: pages: write` 和 `id-token: write` 時，OIDC 驗證失敗。

**解決方案**：
```yaml
permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build-and-test:
    steps:
      - uses: actions/upload-pages-artifact@v3  # 專用 action
        with:
          path: allure-report/

  deploy-pages:
    needs: build-and-test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment:
      name: github-pages
    steps:
      - uses: actions/deploy-pages@v4
```

**經驗總結**：PR 只觸發測試不部署（`if: github.event_name == 'push'`），避免每個 PR 都蓋掉正式報告，這是 CI/CD 的標準保護機制。