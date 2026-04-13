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

