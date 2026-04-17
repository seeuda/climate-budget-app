# 彰化縣氣候預算導引式判讀系統（Climate Budget App）

本專案為以 **Streamlit** 建置的「氣候預算導引式判讀系統」，主要用於協助使用者：

- 輸入計畫內容與預算資訊
- 透過關鍵字與邏輯規則判斷案件與氣候議題之關聯性
- 產出可追溯的判讀結果（包含規則版本、命中理由、明細資料）
- 視需要將結果同步到 Google 試算表

目前系統程式已更新至 **v1.4**（功能層），規則資料仍沿用 **v1.3.7**（`data/config.json` 的 `config_version`）。

本次 v1.4 版本重點包含：
- 新增「補充文件上傳」流程（可多檔拖曳上傳至 Google Drive 私有資料夾）
- 匯出/狀態資料加入已上傳文件清單，提升案件追溯能力
- 強化欄位對應、明細輸出格式與 anti-pattern 診斷骨幹

---

## 1. 專案重點

- **雙入口策略**
  - `app.py`：Streamlit 入口；預設載入主應用，並提供 `?health_check=1` 的啟動檢查頁。
  - `update_manifest.py`：主要判讀流程與資料輸出邏輯。

- **版本可追溯**
  - 規則與資料版本集中於 `data/config.json` 的 `schema_version` / `manifest`。
  - 程式功能版本（`update_manifest.py`）與規則版本（`config_version`）可分層管理。
  - 同步輸出可附帶規則版本資訊，方便稽核與回溯。

- **v1.4 新增補充文件上傳**
  - 在結果頁可上傳「工作內容說明文件」（支援多檔拖曳）。
  - 單檔上限 200MB，會自動略過重複上傳檔案。
  - 上傳成功後會在畫面顯示文件名稱、大小與上傳時間。

- **部署導向健檢**
  - 針對常見部署失敗（如 requirements 格式錯誤、入口檔異常、設定檔不可解析）提供可視化檢查頁。

---

## 2. 目錄說明

```text
.
├─ app.py                       # Streamlit 入口（主程式 + health check）
├─ update_manifest.py           # 主要判讀流程（含 v1.4 補充文件上傳）與報告/同步整合邏輯
├─ data/
│  └─ config.json               # 規則設定、版本資訊、系統參數
├─ requirements.txt             # Python 相依套件
├─ TROUBLESHOOTING.md           # 常見部署錯誤與排查建議
├─ scripts/
│  ├─ check_duplicate_ids.py    # trigger_id 重複檢查工具（可執行版）
│  └─ test_keyword_regression.py# 關鍵字回歸測試腳本（可執行版）
├─ check_duplicate_ids.py       # 舊版/歷史檔（非主要執行入口）
└─ test_keyword_regression.py   # 舊版/歷史檔（非主要執行入口）
```

---

## 3. 開發環境需求

- Python 3.10+
- 建議使用虛擬環境（venv / conda 均可）

安裝步驟：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. 本機啟動方式

### 一般啟動

```bash
streamlit run app.py
```

### 啟動檢查頁（排查部署問題）

```text
http://localhost:8501/?health_check=1
```

健康檢查頁會重點檢查：
- `app.py` 是否可編譯
- `requirements.txt` 是否為合法需求格式
- `config.json` / `data/config.json` 是否可解析

---

## 5. 版本管理原則（建議）

建議採 **雙軌 SemVer**（語意化版本）：

- **App Version（程式功能層）**：例如 `1.4.0`
  - **Major（X.0.0）**：不相容改動（流程、欄位結構、整合介面大幅調整）
  - **Minor（1.X.0）**：新增功能且向下相容（如新增上傳、匯出能力）
  - **Patch（1.4.X）**：修正 bug、UI 微調、效能與穩定性改善
- **Rules Version（規則層）**：例如 `1.3.7`（`data/config.json` 的 `config_version`）
  - 專注在關鍵字、邏輯映射、誤判防呆等判讀規則變更

### 版本拉齊建議（避免混淆）

- **對外發布時建議拉齊 Major.Minor**：例如 `App 1.4.x` 搭配 `Rules 1.4.x`。
- 內部快速迭代可短暫不一致（如 `App 1.4.0` + `Rules 1.3.7`），但需在首頁/匯出欄位同時顯示兩者版本。
- 若只有規則調整且程式未改，可只升 `Rules patch`；若程式流程改動，至少升 `App minor/patch` 並在 release note 說明相依的 Rules 最低版本。
- 為降低一般使用者混淆，前台主畫面建議只顯示單一「系統版本（App）」；`Rules Version` 保留於匯出 JSON / 管理資訊即可。

---

## 6. 測試與檢核

### 語法檢查

```bash
python -m py_compile app.py update_manifest.py
```

### 關鍵字回歸（依專案腳本）

```bash
python scripts/test_keyword_regression.py
```

### trigger_id 唯一性檢查

```bash
python scripts/check_duplicate_ids.py
```

---

## 7. v1.4 補充文件上傳設定（Google Drive）

若要啟用「補充文件上傳」功能，部署環境需提供下列資訊：

- `google_drive_upload_folder_id`（或相容鍵：`drive_upload_folder_id` / `supporting_docs_drive_folder_id`）
- OAuth 相關 secrets：
  - `google_oauth_client_id`
  - `google_oauth_client_secret`
  - `google_oauth_refresh_token`

功能行為說明：
- 入口為結果頁的「📤 上傳補充文件」按鈕（先選檔、再按鈕正式上傳）。
- 支援多檔與拖曳上傳。
- 系統會以檔名 + 檔案內容摘要產生簽章，避免同一檔案重複上傳。
- 上傳結果會同步記錄於 session state 及匯出資料（`uploaded_supporting_files`）。

---

## 8. 部署注意事項

- 部署前確認 `requirements.txt` 每行皆為合法 pip 規格。
- 確認入口仍為 `app.py`，且為 Python 程式（非 JSON / binary）。
- 若部署平台顯示 `Oh no. Error running app`：
  1. 先開 `?health_check=1` 觀察診斷結果
  2. 參考 `TROUBLESHOOTING.md` 逐項排查

---

## 9. 維運建議

- 任何規則調整都同步更新 `data/config.json` 之版本與 changelog。
- 與外部表單/試算表整合時，保持欄位相容與命名一致。
- 每次發布前執行至少一次語法檢查與關鍵字回歸測試。

---

## 10. 授權

本專案以儲存庫內 `LICENSE` 為準。
