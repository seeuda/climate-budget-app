# App 顯示「Oh no. Error running app」可能原因（快速檢查）

## 這次實際定位到的根因

1. **`requirements.txt` 不是 pip 套件清單**
   - 部署紀錄已明確出現：`ERROR: Invalid requirement: '"""' (from line 1 of requirements.txt)`。
   - 這會讓安裝依賴階段直接失敗，平台就回傳通用錯誤訊息。

2. **`app.py` 曾是 JSON 型內容而非 Python 程式**
   - 若入口檔含 JSON 布林值（`false`），會在 Python 啟動時報 `NameError`。

3. **`config.json` 內容不像 JSON 文字**
   - 其前導位元組不是 `{` / `[`，疑似錯置為 binary/bytecode。

## 本次修正

- 已將 `requirements.txt` 改為合法依賴格式（至少包含 `streamlit`）。
- 已將 `app.py` 改為可啟動的 Streamlit 健檢頁，避免入口檔語法錯誤造成啟動失敗。

## 若仍遇到錯誤，建議依序檢查

1. `requirements.txt` 是否每行都是套件名稱（例如 `streamlit>=1.56.0,<2`）。
2. `app.py` 第一行是否為 Python 程式（例如 `import ...`），而不是 `{`。
3. `config.json` 是否能被 `json.load()` 解析。
4. 本機先跑：
   - `python -m streamlit run app.py --server.headless true`

---

## Google 試算表同步（細節欄位與查核建議）

若你已在試算表新增下列 4 欄，方向是正確的：

- `細項分類明細(JSON)`：保留 `sub_categories` 原始陣列。
- `氣候工項明細(JSON)`：保留 `counted_items`（含金額、比例、item_id 等）。
- `非預算型效益明細(JSON)`：保留 `non_budget_items_detail`。
- `同步回執碼`：每次送出的唯一識別碼（例如 `SYNC-20260415103045-AB12`）。

### 建議欄位配置

1. **保留既有摘要欄位 + 新增 JSON 明細欄位**（同時兼顧閱讀與稽核）。
2. JSON 欄位建議放在工作表右側，避免影響一般檢視。
3. `同步回執碼` 建議設為查找主鍵（可用篩選或 QUERY / XLOOKUP 查核）。

### 使用者成功確認建議

1. 送出後先看畫面上的「同步成功訊息 + 同步回執碼」。
2. 再到試算表以 `同步回執碼` 搜尋該筆是否存在。
3. 下載 JSON 報告留存（作為送出當下內容的封存證據）。
