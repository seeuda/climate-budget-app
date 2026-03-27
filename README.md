# 🌿 彰化縣氣候預算導引式判讀系統

**Climate Budget Assessment Tool for Changhua County Government**  
版本 v1.2 · 基於國家第三期溫室氣體階段管制目標與各部門行動方案、工程減碳參考作業指引

---

## 📌 系統簡介

本系統協助彰化縣各局處承辦人（非氣候專家），透過直覺式引導流程，判定既有計畫中可能存在的**氣候預算**，並自動對應國家淨零政策框架，產出可供推動會使用的評估報告。

### 核心功能

- 🔍 **關鍵字自動偵測**：輸入標案名稱即自動辨識氣候相關工項，並顯示判讀依據說明
- 🗂️ **多層次複選導引**：計畫類別可複選最多 3 項；每個類別至少須選一個細項
- 💰 **預算拆解防呆**：工項金額以「萬元」為單位輸入，即時顯示剩餘預算；設計型／管理型效益不列入金額計算，另於摘要呈現
- 📐 **工程減量效益記錄**：自動偵測零成本工項，引導填寫土方量、廢棄物量、建材量及其他效益說明
- 📊 **判讀信心評估**：關鍵字命中品質分為高／中／低三級，供管理端優先抽查低信心案件
- 🛡️ **反例提示（anti-pattern）**：自動偵測 10 種常見誤判情境，依嚴重度顯示警示或建議（Phase 1B 啟用）
- 🏷️ **氣候效益相關性標記**：每個工項標記高純度／高相關性／部分相關／低度相關，區分預算型與非預算型效益（Phase 1B 啟用）
- 📤 **雙格式匯出**：JSON（含計算資料與解讀資料分層）與 CSV，同步至 Google 試算表後才可下載
- 🚦 **風險分級警示**：四色燈號依計畫總經費自動判定

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

步驟五設計為**先同步至 Google 試算表，成功後才可下載 JSON / CSV 報告**。目前以 **Service Account 直接寫入**為主，Webhook 模式預留備用。

### Service Account（目前使用）

在 `.streamlit/secrets.toml` 設定：

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

### Webhook（預留備用）

```toml
google_sheet_webhook_url = "https://script.google.com/macros/s/你的部署ID/exec"
```

`data/config.json` 的 `integrations` 區塊可保留 `google_sheet_id` / `google_sheet_worksheet` 作為預設值。

---

## 📁 檔案結構

```
climate-budget-app-test2/
├── app.py                      # 主程式（Streamlit，v1.2）
├── requirements.txt            # 套件需求
├── README.md                   # 本文件
├── LICENSE                     # MIT 授權聲明
├── .streamlit/
│   └── config.toml             # Streamlit 主題設定
├── data/
│   ├── config.json             # 系統設定（v1.2.3）
│   │                           #   門檻、警示文字、局處清單、版本紀錄
│   │                           #   + purity_codes、anti_patterns（10條）
│   │                           #   + department_presets（15局處）
│   │                           #   + adaptation_keyword_layers（3層37詞）
│   │                           #   + manifest（版本管控與 checksum）
│   ├── logic_mapping.json      # 業務邏輯（v1.0.0）
│   │                           #   7大類別、22細項、91工項、政策對應代碼
│   │                           #   + default_purity、benefit_type、item_id（每工項）
│   └── keyword_dictionary.json # 關鍵字庫（v1.0.0）
│                               #   77筆強觸發 + 4筆組合條件規則
│                               #   + trigger_id、weight、purity_hint（每筆）
└── scripts/
    └── update_manifest.py      # JSON 版本與 checksum 更新腳本
```

---

## 🔧 資料維護說明

本系統採**資料與程式分離**設計，政策調整時只需修改 `data/` 目錄下的 JSON 檔案，無需更動主程式。

> ⚠️ **修改任何 JSON 後，請務必執行 checksum 更新腳本：**
> ```bash
> python scripts/update_manifest.py --note "說明本次修改內容"
> ```
> 這會自動偵測哪支檔案有變更、遞增版本號，並更新 `config.json` 的 manifest 區塊。

### 新增關鍵字觸發（`keyword_dictionary.json`）

在 `keyword_triggers` 陣列中新增，**必要欄位全部補齊**：

```json
{
  "trigger_id": "KW_078",
  "keyword": "太陽能板",
  "suggested_item": "屋頂太陽能光電設置",
  "code": "能源-1",
  "category_id": "E",
  "sub_id": "E1",
  "_match_type": "exact",
  "weight": 1.0,
  "purity_hint": "P1_HIGH_PURITY",
  "anti_pattern_ids": [5],
  "synonyms": [],
  "negative_context": [],
  "learning_tip": ""
}
```

`purity_hint` 可用代碼：`P1_HIGH_PURITY` / `P2_HIGH_RELEVANCE` / `P3_PARTIAL` / `P4_LOW` / `P5_MANAGEMENT`

### 新增工項（`logic_mapping.json`）

在對應的 `sub_categories[].items` 陣列中新增，**必要欄位全部補齊**：

```json
{
  "item_id": "ITEM_G3_01",
  "label": "高溫熱危害防護措施",
  "benefit_type": "management",
  "default_purity": "P3_PARTIAL",
  "count_in_budget_total": false,
  "display_section": "non_budget_benefits",
  "adaptation_codes": ["調適-社會"],
  "mitigation_codes": [],
  "policy": "國家調適計畫-健康領域",
  "alert": "",
  "anti_pattern_ref": [],
  "budget_hint": ""
}
```

`benefit_type` 選項：`budget`（預算型）/ `design`（設計型）/ `management`（管理型）

`count_in_budget_total` 與 `display_section` 須與 `benefit_type` 一致：
- `budget` → `true` / `budget_items`
- `design` 或 `management` → `false` / `non_budget_benefits`

### 新增反例提示規則（`config.json`）

在 `anti_patterns` 陣列中新增：

```json
{
  "id": 11,
  "name": "規則名稱",
  "trigger_keywords": ["觸發詞A", "觸發詞B"],
  "require_all_triggers": false,
  "require_context_keywords": [],
  "exclude_keywords": ["排除詞"],
  "severity": "caution",
  "action_type": "suggest_review",
  "warning_text": "⚠ 顯示給使用者的提示文字",
  "default_purity": "P3_PARTIAL",
  "note": "內部說明"
}
```

`severity`：`info`（淡色提示）/ `caution`（黃色警示）/ `warning`（強警示）  
`action_type`：`remind`（僅提示）/ `suggest_review`（建議覆核）/ `require_review`（強制覆核）

### 更新局處預設（`config.json`）

修改 `department_presets` 中對應局處的設定：

```json
"水利資源處": {
  "default_categories": ["B"],
  "category_priority_order": ["B", "D", "F"],
  "adaptation_layer_emphasis": "water_flood",
  "dept_hint": "顯示給承辦人的提示文字",
  "common_anti_pattern_ids": [2, 7]
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

---

## 🔢 純度代碼對照表

| 代碼 | 顯示標籤 | 說明 |
|------|---------|------|
| `P1_HIGH_PURITY` | 高純度氣候工項 | 主要目的即為氣候行動，效益直接且明確 |
| `P2_HIGH_RELEVANCE` | 高相關性氣候工項 | 氣候效益為主要組成之一，具直接關聯 |
| `P3_PARTIAL` | 部分相關氣候工項 | 僅部分工項具氣候效益，其餘屬常規支出 |
| `P4_LOW` | 低度相關氣候工項 | 間接或附帶效益，主要功能非氣候行動 |
| `P5_MANAGEMENT` | 管理型效益 | 施工管理或行政層次，不列入預算金額，僅於摘要呈現 |

---

## 📊 政策代碼對照

| 代碼前綴 | 對應部門 |
|---------|---------|
| 住商-X | 住商部門行動方案 |
| 運輸-X | 運輸部門行動方案 |
| 農業-X | 農業部門行動方案 |
| 環境-X | 環境部門行動方案 |
| 能源-X | 能源部門行動方案 |
| 調適-水 / 調適-降溫 / 調適-生態 / 調適-社會 / 調適-政策 | 氣候調適行動方案 |
| 淨零教育-X | 淨零教育推廣方案 |

---

## 🗂️ 評估流程

```
步驟一：帶入計畫基本資訊（依預載清單選擇或手動輸入）
    ↓ 關鍵字自動偵測，右側即時顯示建議工項與判讀依據說明
步驟二：複選計畫類別（最多 3 項）＋選擇細項分類
    ↓ 每個類別至少須選一個細項，或點選「無適合項目」後才能繼續
步驟三：勾選氣候相關工項
    ↓ ⭐ 標示由關鍵字觸發的建議工項
    ↓ 工項分為「預算型」與「非預算型效益」兩區顯示
步驟四：填寫各工項氣候預算（萬元）
    ↓ 只有 benefit_type=budget 的工項列入總額計算
    ↓ 設計型／管理型工項顯示說明欄，不填金額
    ↓ 有減量工項時，顯示「工程量體縮減及其他效益（選填）」區塊
步驟五：確認結果並同步至 Google 試算表
    ↓ 顯示「判讀信心」、「工項相關性摘要」、「非預算型效益」
    ↓ 同步成功後才可下載
JSON / CSV 雙格式下載（含計算資料與解讀資料分層）
```

---

## 📋 JSON 輸出結構說明（v1.2）

v1.2 起 JSON 輸出明確分為**計算資料**與**解讀資料**兩層，避免金額與相關性標記混淆。

```json
{
  "project_metadata": {
    "uid": "CHC-20260325143022-A3F2-K7X",
    "name": "標案名稱",
    "dept": "主辦局處",
    "total_budget": 22620000,
    "is_manual_override": false,
    "assessment_date": "2026-03-25 14:30",
    "rule_versions": {
      "config_version": "1.2.3",
      "data_version": "1.0.0",
      "kd_version": "1.0.0",
      "lm_version": "1.0.0"
    }
  },
  "budget_summary": {
    "climate_budget_total": 12000000,
    "climate_budget_ratio": 53.1,
    "alert_level": "🔴 氣候預算潛力：部門轉型",
    "counted_items": [
      {
        "label": "工項名稱",
        "amount": 5000000,
        "ratio": 22.1,
        "item_id": "ITEM_B1_01",
        "is_zero_cost": false
      }
    ],
    "categories": ["A", "B"],
    "category_labels": "興建／新建、排水／水利"
  },
  "interpretation_summary": {
    "item_relevance_text": "滯洪池建置（高純度氣候工項）、排水清淤（部分相關氣候工項）",
    "non_budget_benefits": "【設計型】現地土方平衡處理",
    "anti_pattern_hits": [
      {
        "id": 2,
        "name": "排水工程非氣候設計",
        "severity": "caution",
        "action_type": "suggest_review",
        "warning_text": "⚠ 一般維護性排水未必屬氣候調適..."
      }
    ],
    "has_low_relevance_items": false
  },
  "confidence": {
    "level": "high",
    "label": "🟢 高信心",
    "reasons": ["命中 2 個強觸發關鍵字：「護岸」、「滯洪」"]
  },
  "matched_keywords": ["護岸", "滯洪"],
  "matched_trigger_ids": ["KW_041", "KW_004"],
  "assessment_metadata": {
    "user_note": "補充說明文字",
    "system_version": "1.2"
  }
}
```

> 舊版欄位（`climate_budget_total`、`climate_assessment`、`impact_level`）保留至 Phase 2 重構前，確保 Google Sheet 同步向下相容。

---

## 🔄 版本管控說明

### JSON 版本追蹤架構

本系統採「集中管控 + 個別辨識」機制：

- `config.json` 的 `schema_version` 統一記錄整體版本
- `manifest` 區塊記錄各 JSON 檔案的獨立版本號與 MD5 checksum
- 修改任一 JSON 後，執行 `python scripts/update_manifest.py` 自動偵測變更並更新

### 常用指令

```bash
# 確認哪支 JSON 有變更（不寫入）
python scripts/update_manifest.py --dry-run

# 更新並附上說明
python scripts/update_manifest.py --note "新增高溫勞安觸發詞 5 筆"

# 手動指定新版本號（大幅修改時）
python scripts/update_manifest.py --lm-version 1.1.0 --note "G3 子類別新增"
```

---

## 📋 版本紀錄

- **v1.2** (2026-03-26)：Phase 1A 架構升級
  - `config.json` 新增 `purity_codes` enum 定義（5 個代碼，UI 顯示一律查表）
  - `config.json` 新增 `anti_patterns` 10 條反例提示規則（含 severity / action_type / require_context_keywords）
  - `config.json` 新增 `department_presets` 15 個局處預設（含類別優先序）
  - `config.json` 新增 `adaptation_keyword_layers` 三層調適關鍵字（共 37 詞，補白高溫/勞安/NBS）
  - `config.json` 新增 `manifest` 版本管控區塊（個別 JSON checksum 追蹤）
  - `keyword_dictionary.json` 所有 77 筆 trigger 補入 `trigger_id`、`weight`、`purity_hint`（enum code）、`anti_pattern_ids`
  - `logic_mapping.json` 所有 91 個工項補入 `item_id`、`default_purity`（enum code）、`benefit_type`、`count_in_budget_total`、`display_section`
  - `app.py` 新增 `purity_label()` / `purity_color()` 查表函式，UI 不硬寫中文文案
  - `app.py` 新增 `anti_pattern_check()` / `anti_pattern_check_items()` / `merge_anti_pattern_hits()` 完整骨幹
  - `app.py` 新增 `get_dept_preset()` / `apply_dept_preset()` 局處預設骨幹（Phase 1B 啟用）
  - `app.py` `generate_export_json()` 重構：明確分 `budget_summary` 與 `interpretation_summary` 兩層
  - `app.py` `resolve_header_key()` 強化：三步驟精確比對，不唯一時明確拒絕
  - `app.py` `init_state()` 型別穩定化：新增 4 個 Phase 1B 預留欄位
  - `DEFAULT_SYNC_HEADERS` 與 `HEADER_ALIAS_MAP` 重構：分計算資料／解讀資料兩組
  - 新增 `scripts/update_manifest.py` checksum 更新腳本

- **v1.1** (2026-03-19)：Phase 1 功能強化
  - 新增判讀理由面板、關鍵字信心評估、工程量體縮減欄位
  - UID 格式強化（秒數 + 案名 Hash + 隨機碼）
  - `config.json` 新增 `schema_version` 版本管理區塊

- **v1.0** (2026-03)：MVP 初版，整合彰化縣 2025 年決標資料與第三期淨零政策框架

---

## 📞 技術支援

如需擴充局處工項、調整政策代碼或新增關鍵字，請修改 `data/` 目錄下的 JSON 檔案，詳見上方「資料維護說明」，並執行 `update_manifest.py` 更新版本紀錄。

歡迎透過 GitHub Issues 回報問題或提出改善建議。
