# 彰化縣氣候預算導引式判讀系統（Climate Budget App）

本專案為以 **Streamlit** 建置的「氣候預算導引式判讀系統」，主要用於協助使用者：

- 輸入計畫內容與預算資訊
- 透過關鍵字與邏輯規則判斷案件與氣候議題之關聯性
- 產出可追溯的判讀結果（包含規則版本、命中理由、明細資料）
- 視需要將結果同步到 Google 試算表

目前規則版本主軸已進入 **v1.3** 系列（`config_version: 1.3.7`），並持續優化語意判讀與同步欄位相容性。

---

## 1. 專案重點

- **雙入口策略**
  - `app.py`：Streamlit 入口；預設載入主應用，並提供 `?health_check=1` 的啟動檢查頁。
  - `update_manifest.py`：主要判讀流程與資料輸出邏輯。

- **版本可追溯**
  - 規則與資料版本集中於 `data/config.json` 的 `schema_version` / `manifest`。
  - 同步輸出可附帶規則版本資訊，方便稽核與回溯。

- **部署導向健檢**
  - 針對常見部署失敗（如 requirements 格式錯誤、入口檔異常、設定檔不可解析）提供可視化檢查頁。

---

## 2. 目錄說明

```text
.
├─ app.py                       # Streamlit 入口（主程式 + health check）
├─ update_manifest.py           # 主要判讀流程與報告/同步整合邏輯
├─ data/
│  └─ config.json               # 規則設定、版本資訊、系統參數
├─ requirements.txt             # Python 相依套件
├─ TROUBLESHOOTING.md           # 常見部署錯誤與排查建議
├─ check_duplicate_ids.py       # trigger_id 重複檢查工具
└─ test_keyword_regression.py   # 關鍵字回歸測試腳本
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

建議採 **SemVer**（語意化版本）：

- **Major（X.0.0）**：不相容改動（欄位或行為大幅變更）
- **Minor（1.X.0）**：新增功能且向下相容
- **Patch（1.3.X）**：修正錯誤或語意優化，不改變主要介面

目前可將系統定位為：
- 規則主線：`v1.3.x`
- 若僅微調語意／修補相容性，建議遞增 patch（如 1.3.8）
- 若新增一組明顯新能力且仍相容，才升 minor（如 1.4.0）

---

## 6. 測試與檢核

### 語法檢查

```bash
python -m py_compile app.py update_manifest.py
```

### 關鍵字回歸（依專案腳本）

```bash
python test_keyword_regression.py
```

### trigger_id 唯一性檢查

```bash
python check_duplicate_ids.py
```

---

## 7. 部署注意事項

- 部署前確認 `requirements.txt` 每行皆為合法 pip 規格。
- 確認入口仍為 `app.py`，且為 Python 程式（非 JSON / binary）。
- 若部署平台顯示 `Oh no. Error running app`：
  1. 先開 `?health_check=1` 觀察診斷結果
  2. 參考 `TROUBLESHOOTING.md` 逐項排查

---

## 8. 維運建議

- 任何規則調整都同步更新 `data/config.json` 之版本與 changelog。
- 與外部表單/試算表整合時，保持欄位相容與命名一致。
- 每次發布前執行至少一次語法檢查與關鍵字回歸測試。

---

## 9. 授權

本專案以儲存庫內 `LICENSE` 為準。
