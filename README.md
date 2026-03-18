# 🌿 彰化縣氣候預算導引式判讀系統

**Climate Budget Assessment Tool for Changhua County Government**  
版本 v1.0 · 基於國家第三期溫室氣體階段管制目標

---

## 📌 系統簡介

本系統協助彰化縣各局處承辦人（非氣候專家），透過直覺式引導流程，判定既有計畫中可能存在的**氣候預算**，並自動對應國家淨零政策框架，產出可供推動會使用的評估報告。

### 核心功能
- 🔍 **關鍵字自動偵測**：輸入標案名稱即自動辨識氣候相關工項
- 🗂️ **多層次導引**：計畫類別可複選最多 3 項，並聯合顯示細項分類與具體工項
- 💰 **預算拆解防呆**：即時顯示剩餘預算、鎖定超額送出
- 📤 **雙格式匯出**：JSON（系統串接）與 CSV（Excel分析）
- 🚦 **風險分級警示**：四色燈號自動判定（300萬/1000萬/2000萬/1億）

---

## 🚀 快速部署

### 方式一：Streamlit Community Cloud（建議）

1. Fork 本 Repository 至您的 GitHub 帳號
2. 前往 [share.streamlit.io](https://share.streamlit.io)
3. 點選「New app」，選擇本 Repo
4. 主程式設定為：`app.py`
5. 點選「Deploy」即可

### 方式二：本地端執行

```bash
# 1. Clone 專案
git clone https://github.com/YOUR_ACCOUNT/climate-budget-app.git
cd climate-budget-app

# 2. 安裝套件
pip install -r requirements.txt

# 3. 啟動
streamlit run app.py
```

---


### Google 試算表同步設定（必要）

步驟五已改為：**先同步至預設 Google 試算表，成功後才可下載 JSON/CSV**。

支援兩種同步模式（擇一）：

1. **Webhook 模式（原本做法）**
   在 `.streamlit/secrets.toml` 設定：

   ```toml
   google_sheet_webhook_url = "https://script.google.com/macros/s/你的部署ID/exec"
   google_sheet_id = "你的試算表ID"
   google_sheet_worksheet = "工作表1"
   ```

2. **Service Account 直接寫入（新做法）**
   若未設定 webhook，系統會改用 service account 直接 append。

   ```toml
   google_sheet_id = "10Z_wgmfqv4h4rk4oKDsP-V4jSS9XmO6PGAy_jrpTU7Q"
   google_sheet_worksheet = "工作表1"

   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "changhuaclimate@elated-parser-486413-m5.iam.gserviceaccount.com"
   client_id = "..."
   token_uri = "https://oauth2.googleapis.com/token"
   ```

`data/config.json` 可保留 `integrations.google_sheet_id / google_sheet_worksheet` 作為預設值。

### 2026/03 清單分析後的規則補強

- 門檻維持 300 萬元，並在低於門檻時新增「排水清疏/災修」的人工覆核提示。
- 補強關鍵字字典：`清疏`、`護岸`、`防洪`、`抽水`、`拓寬`、`新建`、`宿舍`、`住宅`、`環境教育`、`資收`。
- 新增跨局處共用工項「場館室內裝修（通用節能檢核）」與 `F3` 子類「科學監測與政策研究」。
- 新增中央第三期對接欄位：七大工程減碳指引分類、綠色預算支出分類、公正轉型標記（輸出於 `assessment_metadata`）。
- `logic_mapping.json` 新增 `engineering_guideline_types` 與 `central_sector_strategies`，並在工項加入 `central_alignment` / `green_spending_type`。

## 📁 檔案結構

```
climate_budget_app/
├── app.py                      # 主程式（Streamlit）
├── requirements.txt            # 套件需求
├── README.md                   # 本文件
└── data/
    ├── config.json             # 系統設定（門檻、警示文字、局處清單）
    ├── logic_mapping.json      # 業務邏輯（類別、工項、方案代碼）
    └── keyword_dictionary.json # 關鍵字庫（標案名稱自動偵測）
```

---

## 🔧 資料維護說明

本系統採**資料與代碼分離**設計，日後只需修改 JSON 檔案，不需更動主程式。

### 新增關鍵字觸發（`keyword_dictionary.json`）
```json
{
  "keyword": "太陽能板",
  "suggested_item": "屋頂太陽能光電設置",
  "code": "能源-1",
  "category_id": "E",
  "sub_id": "E1"
}
```

### 新增工項（`logic_mapping.json`）
在對應的 `sub_categories.items` 陣列中新增：
```json
{
  "label": "新工項名稱",
  "mitigation_codes": ["住商-X"],
  "adaptation_codes": [],
  "policy": "第三期XX部門：說明",
  "alert": "（選填）特殊警示文字"
}
```

### 調整預算門檻（`config.json`）
修改 `system_parameters` 中的數值即可：
```json
"min_threshold": 3000000,
"medium_alert_threshold": 10000000,
"high_alert_threshold": 20000000,
"extreme_alert_threshold": 100000000
```

---

## 📊 方案代碼對照

| 代碼前綴 | 對應部門 |
|---------|---------|
| 住商-X | 住商部門行動方案 |
| 運輸-X | 運輸部門行動方案 |
| 農業-X | 農業部門行動方案 |
| 環境-X | 環境部門行動方案 |
| 能源-X | 能源部門行動方案 |
| 調適-X | 氣候調適行動方案 |
| 淨零教育-X | 淨零教育推廣方案 |

---

## 🗂️ 評估流程

```
步驟一：輸入計畫基本資訊
    ↓ （關鍵字自動偵測）
步驟二：複選計畫類別（最多 3 項）
    ↓ （系統高亮建議類別，可隨時補選）
步驟三：複選細項分類與氣候相關工項
    ↓ （依已選類別/細項聯集顯示，可複選，含方案代碼）
步驟四：拆解各工項預算比例
    ↓ （剩餘預算即時顯示）
步驟五：確認結果並匯出報告
    ↓
JSON / CSV 雙格式下載
```

---

## 📋 版本紀錄

- **v1.0** (2026-03)：MVP 初版，整合彰化縣2025年決標資料與第三期淨零政策

---

## 📞 技術支援

如需擴充局處工項或調整政策代碼，請修改 `data/` 目錄下的 JSON 檔案。  
歡迎透過 GitHub Issues 回報問題或建議。
