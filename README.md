# 🌿 彰化縣氣候預算導引式判讀系統

**Climate Budget Assessment Tool for Changhua County Government**  
版本 v1.1 · 基於國家第三期溫室氣體階段管制目標與各部門行動方案、工程減碳參考作業指引

---

## 📌 系統簡介

本系統協助彰化縣各局處承辦人（非氣候專家），透過直覺式引導流程，判定既有計畫中可能存在的**氣候預算**，並自動對應國家淨零政策框架，產出可供推動會使用的評估報告。

### 核心功能

- 🔍 **關鍵字自動偵測**：輸入標案名稱即自動辨識氣候相關工項，並顯示判讀依據說明
- 🗂️ **多層次複選導引**：計畫類別可複選最多 3 項；每個類別至少須選一個細項，或點選「無適合項目」後才能繼續
- 💰 **預算拆解防呆**：工項金額以「萬元」為單位輸入，即時顯示剩餘預算；不花錢／少花錢的工法自動識別，免填金額或允許填 0
- 📐 **工程減量效益記錄**：自動偵測零成本工項，引導填寫土方量、廢棄物量、建材量及其他效益說明
- 📊 **雙層信心評估**：「關鍵字信心評估」（標案名稱命中情形）＋「工程減量資訊完整度」（有勾選減量工項時才顯示）
- 📤 **雙格式匯出**：JSON（供系統串接）與 CSV（供 Excel 分析），同步至 Google 試算表後才可下載
- 🚦 **風險分級警示**：四色燈號依計畫總經費自動判定（300萬 / 1000萬 / 2000萬 / 1億）
- 🛡️ **工項保護機制**：補選或取消類別、細項時不清空既有工項，僅在進入下一步時移除已失效工項

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
# 1. 下載專案
git clone https://github.com/YOUR_ACCOUNT/climate-budget-app.git
cd climate-budget-app

# 2. 安裝套件
pip install -r requirements.txt

# 3. 啟動
streamlit run app.py
```

---

## ⚙️ Google 試算表同步設定

步驟五設計為**先同步至 Google 試算表，成功後才可下載 JSON / CSV 報告**。支援兩種同步模式（擇一）：

### 模式一：Webhook（Google Apps Script）

在 `.streamlit/secrets.toml` 設定：

```toml
google_sheet_webhook_url = "https://script.google.com/macros/s/你的部署ID/exec"
google_sheet_id = "你的試算表ID"
google_sheet_worksheet = "工作表1"
```

### 模式二：Service Account 直接寫入

若未設定 webhook，系統自動改用 service account 直接 append：

```toml
google_sheet_id = "你的試算表ID"
google_sheet_worksheet = "工作表1"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

`data/config.json` 的 `integrations` 區塊可保留 `google_sheet_id` / `google_sheet_worksheet` 作為預設值。

---

## 📁 檔案結構

```
climate-budget-app-test2/
├── app.py                      # 主程式（Streamlit）
├── requirements.txt            # 套件需求
├── README.md                   # 本文件
├── LICENSE                     # MIT 授權聲明
├── .streamlit/
│   └── config.toml             # Streamlit 主題設定
└── data/
    ├── config.json             # 系統設定（門檻、警示文字、局處清單、版本紀錄）
    ├── logic_mapping.json      # 業務邏輯（7大類別、22細項、88工項、政策對應代碼）
    └── keyword_dictionary.json # 關鍵字庫（77筆強觸發 + 4筆組合條件規則）
```

---

## 🔧 資料維護說明

本系統採**資料與程式分離**設計，政策調整時只需修改 `data/` 目錄下的 JSON 檔案，無需更動主程式。

### 新增關鍵字觸發（`keyword_dictionary.json`）

在 `keyword_triggers` 陣列中新增：

```json
{
  "keyword": "太陽能板",
  "suggested_item": "屋頂太陽能光電設置",
  "code": "能源-1",
  "category_id": "E",
  "sub_id": "E1",
  "_match_type": "exact"
}
```

組合條件規則（需同時出現多個關鍵字）加入 `keyword_logic` 陣列：

```json
{
  "triggers": ["租賃", "公務車"],
  "suggested_item": "車輛租賃低碳化（限電動車/油電車）",
  "category_id": "C",
  "sub_id": "C2",
  "_match_type": "logic",
  "note": "需同時出現：租賃＋公務車"
}
```

### 新增工項（`logic_mapping.json`）

在對應的 `sub_categories[].items` 陣列中新增：

```json
{
  "label": "新工項名稱",
  "mitigation_codes": ["住商-X"],
  "adaptation_codes": [],
  "policy": "第三期XX部門：說明",
  "alert": "（選填）特殊警示文字"
}
```

### 暫時關閉細項（`logic_mapping.json`）

在細項物件加入 `"enabled": false`，資料與政策代碼保留不刪除，日後移除此欄位即可重新啟用：

```json
{
  "id": "C3",
  "label": "軌道與鐵道系統優化",
  "enabled": false,
  "disabled_reason": "彰化縣目前無軌道業務，暫時關閉"
}
```

### 調整預算門檻（`config.json`）

修改 `system_parameters` 中的數值（單位：元）：

```json
"min_threshold": 3000000,
"medium_alert_threshold": 10000000,
"high_alert_threshold": 20000000,
"extreme_alert_threshold": 100000000
```

### 版本紀錄管理（`config.json`）

每次修改 JSON 資料後，請同步更新 `schema_version` 區塊：

```json
"schema_version": {
  "config_version": "1.1.0",
  "effective_date": "2026-03-19",
  "updated_by": "氣候變遷科",
  "change_log": ["v1.1.0: 說明修改內容"]
}
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
步驟一：帶入計畫基本資訊（依預載清單選擇或手動輸入）
    ↓ 關鍵字自動偵測，右側即時顯示建議工項與判讀依據說明
步驟二：複選計畫類別（最多 3 項）＋選擇細項分類
    ↓ 每個類別至少須選一個細項，或點選「無適合項目，在下一頁展開氣候工項檢查」
    ↓ 補選或取消類別時，既有工項勾選不會被清空
步驟三：勾選氣候相關工項
    ↓ 依所有已選細項聯集顯示，⭐ 標示由關鍵字觸發的建議工項
    ↓ 關鍵字觸發的工項下方顯示來源關鍵字標籤
步驟四：填寫各工項氣候預算（萬元）
    ↓ 純零成本工項（現地土方平衡等）不顯示金額欄，引導填效益說明
    ↓ 聰明使用型工項（CLSM、循環建材等）保留金額欄，允許填 0
    ↓ 有減量工項時，顯示「工程量體縮減及其他效益（選填）」區塊
步驟五：確認結果並同步至 Google 試算表
    ↓ 右側顯示「關鍵字信心評估」與「工程減量資訊完整度」（如適用）
    ↓ 同步成功後才可下載
JSON / CSV 雙格式下載
```

---

## 📋 JSON 輸出結構說明

```json
{
  "project_metadata": {
    "uid": "CHC-20260319143022-A3F2-K7X",
    "name": "標案名稱",
    "dept": "主辦局處",
    "total_budget": 22620000,
    "is_manual_override": false,
    "assessment_date": "2026-03-19 14:30"
  },
  "climate_assessment": {
    "categories": ["A", "B"],
    "category_labels": "興建／新建、排水／水利",
    "sub_categories": ["A1", "B1"],
    "sub_category_labels": "低碳工程設計、排水防洪工程",
    "selected_items": [
      {"label": "工項名稱", "amount": 5000000, "is_zero_cost": false}
    ],
    "alert_level": "🔴 氣候預算潛力：部門轉型"
  },
  "climate_budget_total": 12000000,
  "impact_level": "red",
  "confidence": {
    "level": "low",
    "label": "🔴 低信心",
    "desc": "無關鍵字佐證，全部依人工選擇，建議加強說明",
    "reasons": ["未命中任何關鍵字，工項依人工判斷填入"]
  },
  "reduction_completeness": {
    "level": "high",
    "label": "🟢 完整",
    "filled_count": 2,
    "desc": "已提供 2/4 項效益佐證資料"
  },
  "matched_keywords": ["護岸", "滯洪"],
  "physical_reductions": {
    "soil_reduction_ton": 10000,
    "waste_reduction_ton": 0,
    "cement_reduction_ton": 0,
    "other_benefit_note": "採用砌石護岸取代混凝土"
  },
  "assessment_metadata": {
    "user_note": "補充說明文字",
    "system_version": "1.1"
  }
}
```

---

## 📋 版本紀錄

- **v1.1** (2026-03-19)：Phase 1 功能強化
  - 新增判讀理由面板：每筆關鍵字觸發顯示來源、類型與對應工項
  - 新增關鍵字信心評估（高/中/低）及工程減量資訊完整度指標
  - 新增工程量體縮減及其他效益欄位（土方量、廢棄物量、建材量、其他說明）
  - 零成本工項（現地土方平衡等）自動識別，免填金額；聰明使用型（CLSM 等）保留金額欄
  - 細項選取改為強制選取，各類別末尾加「無適合項目」逃生出口
  - 工項金額輸入改為萬元單位，空白 placeholder 避免預填干擾
  - UID 格式強化（含秒數 + 案名 Hash + 隨機碼），杜絕碰號
  - C3「軌道與鐵道系統優化」細項設為 `enabled: false`（保留資料，暫時關閉）
  - 下拉選單改為依試算表原始順序排列
  - `config.json` 新增 `schema_version` 版本管理區塊
  - `keyword_dictionary.json` 補齊 `_match_type` 欄位

- **v1.0** (2026-03)：MVP 初版，整合彰化縣 2025 年決標資料與第三期淨零政策框架

---

## 📞 技術支援

如需擴充局處工項、調整政策代碼或新增關鍵字，請修改 `data/` 目錄下的 JSON 檔案，詳見上方「資料維護說明」。

歡迎透過 GitHub Issues 回報問題或提出改善建議。
