"""
彰化縣氣候預算導引式判讀系統
Climate Budget Assessment Tool for Changhua County Government
v1.2 — Phase 1A: JSON框架擴充、purity_codes查表、export結構分層、
        resolve_header_key強化、init_state型別穩定化、
        anti_pattern_check骨幹、manifest版本管控
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from datetime import datetime
TZ_TAIPEI = __import__('datetime').timezone(__import__('datetime').timedelta(hours=8))
import io
import random
import string
import re
from urllib import request, error
import hashlib
import gspread
from google.oauth2.service_account import Credentials

PRESET_SHEET_ID = "1jnAL5LCetC_wBvbAzBqVRD3RPV-KU94xn7MJFX8rVow"
PRESET_SHEET_GID = "0"

# ── Google Sheet 同步：輸出欄位定義 ───────────────────────────────────────────
# 分兩組：計算資料（budget_summary）與解讀資料（interpretation_summary）
# 同步至試算表時合併為單一列；未來儀表板可依此分組聚合

# 計算資料欄位（直接反映金額計算結果）
BUDGET_SUMMARY_HEADERS = [
    "填報日期",
    "案件編號",
    "標案名稱",
    "主辦單位",
    "決標金額",
    "氣候預算",
    "氣候預算比例%",
    "計畫類別",
    "細項分類",
    "氣候工項（預算型）",    # count_in_budget_total=True 的工項
    "關鍵字信心",
    "命中關鍵字",
    "規則版本",
]

# 解讀資料欄位（相關性標記、非預算型效益、診斷資訊）
INTERPRETATION_SUMMARY_HEADERS = [
    "非預算型效益",           # benefit_type=design/management 的工項說明
    "工項相關性摘要",          # 各工項 purity label 的文字摘要
    "anti_pattern命中",       # 觸發的 anti_pattern id 與名稱
    "減量資訊完整度",
    "工程量體縮減效益",
    "國家關鍵戰略 (戰略層面 - Why)",
    "計畫工法類別 (技術層面 - What)",
    "氣候屬性 (功能層面 - How)",
    "潛在減緩/減碳亮點 (實務細節 - Action A)",
    "潛在調適/韌性亮點 (實務細節 - Action B)",
    "防呆提醒",
    "補充說明",
]

DEFAULT_SYNC_HEADERS = BUDGET_SUMMARY_HEADERS + INTERPRETATION_SUMMARY_HEADERS

# ── HEADER_ALIAS_MAP：精準比對優先，模糊比對白名單 ─────────────────────────────
# 設計原則（Phase 1A 強化）：
#   1. 精確相等優先（已在 resolve_header_key 中實作）
#   2. 只比對 alias 白名單，不做自由形式的「包含」比對
#   3. 相似但不唯一的詞彙不列入 alias（避免誤配）
#   4. 同一個 alias 只能對應一個標準 key（alias 不重複）
HEADER_ALIAS_MAP = {
    # ── 計算資料欄位 ────────────────────────────────────────────────────────
    "填報日期"          : ["填報日期", "填報時間", "日期時間"],
    "案件編號"          : ["案件編號", "案號", "uid", "UID"],
    "標案名稱"          : ["標案名稱", "計畫名稱", "案件名稱"],
    "主辦單位"          : ["主辦單位", "主辦局處", "局處名稱", "承辦單位"],
    "決標金額"          : ["決標金額", "預算金額", "計畫金額"],
    "氣候預算"          : ["氣候預算", "氣候預算合計", "氣候相關經費", "氣候經費"],
    "氣候預算比例%"     : ["氣候預算比例%", "氣候預算比例", "氣候比例"],
    "計畫類別"          : ["計畫類別", "判讀主類別", "主類別"],
    "細項分類"          : ["細項分類", "判讀子類別", "子類別"],
    "氣候工項（預算型）": ["氣候工項（預算型）", "氣候工項", "工項清單", "預算型工項"],
    "關鍵字信心"        : ["關鍵字信心", "判讀信心", "信心等級"],
    "命中關鍵字"        : ["命中關鍵字", "觸發關鍵字", "命中詞彙"],
    "規則版本"          : ["規則版本", "config_version", "data_version"],
    # ── 解讀資料欄位 ────────────────────────────────────────────────────────
    "非預算型效益"      : ["非預算型效益", "設計型效益", "管理型效益", "效益補充"],
    "工項相關性摘要"    : ["工項相關性摘要", "純度摘要", "相關性標記"],
    "anti_pattern命中" : ["anti_pattern命中", "誤判提示", "反例命中"],
    "減量資訊完整度"    : ["減量資訊完整度", "減量完整度", "工程減量完整度"],
    "工程量體縮減效益"  : ["工程量體縮減效益", "量體縮減效益", "縮減效益"],
    "國家關鍵戰略 (戰略層面 - Why)": ["國家關鍵戰略 (戰略層面 - Why)", "國家關鍵戰略", "戰略層面-Why", "戰略層面 Why"],
    "計畫工法類別 (技術層面 - What)": ["計畫工法類別 (技術層面 - What)", "計畫工法類別", "技術層面-What", "技術層面 What"],
    "氣候屬性 (功能層面 - How)": ["氣候屬性 (功能層面 - How)", "氣候屬性", "功能層面-How", "功能層面 How"],
    "潛在減緩/減碳亮點 (實務細節 - Action A)": ["潛在減緩/減碳亮點 (實務細節 - Action A)", "潛在減緩/減碳亮點", "Action A"],
    "潛在調適/韌性亮點 (實務細節 - Action B)": ["潛在調適/韌性亮點 (實務細節 - Action B)", "潛在調適/韌性亮點", "Action B"],
    "防呆提醒"          : ["防呆提醒", "防呆", "提醒"],
    "補充說明"          : ["補充說明", "補充說明（選填）", "備註說明", "承辦人備註"],
}

PRESET_REFERENCE_COLUMNS = {
    "national_strategy_why": {
        "label": "國家關鍵戰略 (戰略層面 - Why)",
        "patterns": ["國家關鍵戰略", "戰略層面", "why"],
    },
    "methodology_what": {
        "label": "計畫工法類別 (技術層面 - What)",
        "patterns": ["計畫工法類別", "技術層面", "what"],
    },
    "climate_attribute_how": {
        "label": "氣候屬性 (功能層面 - How)",
        "patterns": ["氣候屬性", "功能層面", "how"],
    },
    "mitigation_highlight_action_a": {
        "label": "潛在減緩/減碳亮點 (實務細節 - Action A)",
        "patterns": ["潛在減緩", "減碳亮點", "action a"],
    },
    "adaptation_highlight_action_b": {
        "label": "潛在調適/韌性亮點 (實務細節 - Action B)",
        "patterns": ["潛在調適", "韌性亮點", "action b"],
    },
    "foolproof_notice": {
        "label": "防呆提醒",
        "patterns": ["防呆提醒", "防呆"],
    },
}


def normalize_text_key(text: str) -> str:
    """Normalize text for resilient column-name matching."""
    return re.sub(r"\s+", "", str(text or "")).lower()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="彰化縣氣候預算判讀系統",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load JSON data ─────────────────────────────────────────────────────────────
def _file_hash(path):
    """回傳檔案內容 MD5，供 load_json 快取失效偵測使用。"""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

@st.cache_data(show_spinner=False)
def load_json(path, _file_hash=""):
    """載入 JSON；_file_hash 參數讓快取在檔案內容變更時自動失效。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_json("data/config.json", _file_hash=_file_hash("data/config.json"))
LOGIC  = load_json("data/logic_mapping.json", _file_hash=_file_hash("data/logic_mapping.json"))
KWDICT = load_json("data/keyword_dictionary.json", _file_hash=_file_hash("data/keyword_dictionary.json"))

PARAMS = CONFIG["system_parameters"]
UI     = CONFIG["ui_text"]
EXPANDER_HINT_TEXT = "ℹ️ 點選下方標題左側的符號（> / ▸）可展開或收合說明。"

# ── Phase 1A：從 config.json 讀取擴充結構 ─────────────────────────────────────

# purity_codes 查表：P1_HIGH_PURITY → {label, desc, color}
# UI 顯示一律走此查表，不在程式裡硬寫中文字串
PURITY_CODES: dict = CONFIG.get("purity_codes", {})

def purity_label(code: str) -> str:
    """code → 中文顯示標籤，找不到時回傳 code 本身。"""
    return PURITY_CODES.get(code, {}).get("label", code)

def purity_color(code: str) -> str:
    """code → 顯示顏色 hex，找不到時回傳灰色。"""
    return PURITY_CODES.get(code, {}).get("color", "#888888")

# anti_patterns：id → 完整 dict，方便 O(1) 查找
ANTI_PATTERNS: dict[int, dict] = {
    ap["id"]: ap for ap in CONFIG.get("anti_patterns", [])
}

# severity → UI 樣式對應（Phase 1B anti_pattern_check UI 使用）
SEVERITY_STYLE: dict[str, dict] = {
    "info":    {"bg": "#f0f8ff", "border": "#4a90d9", "icon": "💡"},
    "caution": {"bg": "#fffbf0", "border": "#f0a500", "icon": "⚠️"},
    "warning": {"bg": "#fff0f0", "border": "#e74c3c", "icon": "🚨"},
}

# department_presets 查表
DEPT_PRESETS: dict = CONFIG.get("department_presets", {})

# config / data 版本（匯出 JSON 時附上，供日後回溯）
_sv = CONFIG.get("schema_version", {})
_mf = CONFIG.get("manifest", {})
CONFIG_VERSION      = _sv.get("config_version", "unknown")
DATA_VERSION        = _sv.get("data_version", "unknown")
KD_VERSION          = _mf.get("keyword_dictionary_version", "unknown")
LM_VERSION          = _mf.get("logic_mapping_version", "unknown")

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #f0f4f0 0%, #e8f0e8 50%, #f0f4f0 100%);
}

.main-header {
    background: linear-gradient(135deg, #1a4731 0%, #2d6a4f 50%, #1a4731 100%);
    color: white;
    padding: 1.2rem 2.25rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}

.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
}

.main-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.8rem;
    font-weight: 400;
    margin: 0;
    letter-spacing: 0.02em;
}

.main-header p {
    font-size: 0.85rem;
    opacity: 0.75;
    margin: 0.3rem 0 0 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Step indicator */
.step-bar {
    display: flex;
    gap: 0;
    margin-bottom: 1.5rem;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.step-item {
    flex: 1;
    padding: 0.7rem 0.5rem;
    text-align: center;
    font-size: 0.78rem;
    font-weight: 500;
    background: #d9e8d9;
    color: #4a7c59;
    border-right: 1px solid rgba(255,255,255,0.5);
    transition: all 0.3s;
}

.step-item.active {
    background: #2d6a4f;
    color: white;
    font-weight: 700;
}

.step-item.done {
    background: #52b788;
    color: white;
}

/* Cards */
.category-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 0.75rem;
    border: 2px solid #e8f0e8;
    cursor: pointer;
    transition: all 0.25s;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.category-card:hover {
    border-color: #2d6a4f;
    box-shadow: 0 4px 16px rgba(45,106,79,0.15);
    transform: translateY(-2px);
}

.category-card.selected {
    border-color: #2d6a4f;
    background: #f0f9f0;
}

.category-card.highlighted {
    border-color: #f39c12;
    background: #fffbf0;
    box-shadow: 0 4px 16px rgba(243,156,18,0.2);
}

/* Alert boxes */
.alert-red {
    background: #fff5f5;
    border-left: 4px solid #e74c3c;
    padding: 0.8rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
    color: #c0392b;
    font-size: 0.88rem;
}

.alert-yellow {
    background: #fffbf0;
    border-left: 4px solid #f39c12;
    padding: 0.8rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
    color: #d68910;
    font-size: 0.88rem;
}

.alert-green {
    background: #f0fdf4;
    border-left: 4px solid #2ecc71;
    padding: 0.8rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
    color: #27ae60;
    font-size: 0.88rem;
}

.alert-purple {
    background: #fdf4ff;
    border-left: 4px solid #8e44ad;
    padding: 0.8rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
    color: #7d3c98;
    font-size: 0.88rem;
}

/* Budget display */
.budget-display {
    background: linear-gradient(135deg, #1a4731, #2d6a4f);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    text-align: center;
    margin: 0.5rem 0;
}

.budget-display .amount {
    font-size: 1.8rem;
    font-weight: 700;
    font-family: 'DM Serif Display', serif;
}

.budget-display .label {
    font-size: 0.78rem;
    opacity: 0.8;
    letter-spacing: 0.05em;
}

.budget-remaining {
    background: linear-gradient(135deg, #27ae60, #2ecc71);
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 10px;
    text-align: center;
}

.budget-over {
    background: linear-gradient(135deg, #c0392b, #e74c3c);
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 10px;
    text-align: center;
}

/* Keyword suggestion */
.kw-suggestion {
    background: linear-gradient(135deg, #fff9e6, #fffbf0);
    border: 1px solid #f0c040;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.85rem;
}

.kw-tag {
    display: inline-block;
    background: #f39c12;
    color: white;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 0.2rem;
}

/* Breadcrumb */
.breadcrumb {
    background: white;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    font-size: 0.82rem;
    color: #555;
    margin-bottom: 1rem;
    border: 1px solid #e0e8e0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* Summary card */
.summary-card {
    background: white;
    border-radius: 14px;
    padding: 1.5rem;
    border: 1px solid #e0e8e0;
    box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    margin-bottom: 1rem;
}

.code-badge {
    display: inline-block;
    background: #2d6a4f;
    color: white;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-family: monospace;
    margin: 0.1rem;
}

/* Item checkbox row */
.item-row {
    padding: 0.5rem 0.7rem;
    border-radius: 8px;
    margin: 0.3rem 0;
    border: 1px solid #eef2ee;
    background: #fafcfa;
    font-size: 0.88rem;
}

.item-row.selected {
    background: #f0f9f0;
    border-color: #52b788;
}

/* Result export section */
.export-section {
    background: linear-gradient(135deg, #1a4731, #2d6a4f);
    color: white;
    border-radius: 14px;
    padding: 2rem;
    margin-top: 1.5rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #1a4731 !important;
}

[data-testid="stSidebar"] * {
    color: #d4e8d4 !important;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #a8d5a8 !important;
}
[data-testid="stSidebar"] button {
    background: rgba(255,255,255,0.15) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}

/* Streamlit button text is rendered in nested elements (e.g. <p>/<span>) */
[data-testid="stSidebar"] button p,
[data-testid="stSidebar"] button span {
    color: #ffffff !important;
}
/* Section headers */
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a4731;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #52b788;
    margin-bottom: 1rem;
}

/* Confidence badges */
.confidence-high {
    display: inline-block;
    background: #27ae60;
    color: white;
    padding: 0.25rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.03em;
}
.confidence-medium {
    display: inline-block;
    background: #f39c12;
    color: white;
    padding: 0.25rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.03em;
}
.confidence-low {
    display: inline-block;
    background: #e74c3c;
    color: white;
    padding: 0.25rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.03em;
}

/* Explainability panel */
.explain-panel {
    background: #fafcff;
    border: 1px solid #bcd4f0;
    border-left: 4px solid #2980b9;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
    font-size: 0.85rem;
}
.explain-panel .explain-title {
    font-weight: 700;
    color: #1a5276;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
}
.explain-row {
    padding: 0.3rem 0;
    border-bottom: 1px solid #e8f0f8;
    font-size: 0.84rem;
    color: #2c3e50;
}
.explain-row:last-child { border-bottom: none; }
.explain-type-strong {
    display: inline-block;
    background: #eaf4fb;
    color: #1a5276;
    border: 1px solid #aed6f1;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.73rem;
    font-weight: 600;
    margin-left: 0.3rem;
}
.explain-type-logic {
    display: inline-block;
    background: #fef9e7;
    color: #7d6608;
    border: 1px solid #f9e79f;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.73rem;
    font-weight: 600;
    margin-left: 0.3rem;
}
.explain-type-budget {
    display: inline-block;
    background: #fdedec;
    color: #922b21;
    border: 1px solid #f5b7b1;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.73rem;
    font-weight: 600;
    margin-left: 0.3rem;
}
.explain-type-manual {
    display: inline-block;
    background: #f4f6f7;
    color: #555;
    border: 1px solid #ccc;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.73rem;
    font-weight: 600;
    margin-left: 0.3rem;
}

/* Exclusion reason box */
.exclusion-reason {
    background: #fff5f5;
    border-left: 4px solid #e74c3c;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.85rem;
    color: #922b21;
}
.exclusion-reason .er-title {
    font-weight: 700;
    margin-bottom: 0.35rem;
}

/* Summary confidence section */
.confidence-summary {
    background: white;
    border: 1px solid #e0e8e0;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
}


button[kind="primary"] {
    background: #2d6a4f !important;
    border: none !important;
    color: #ffffff !important;
}

button[kind="secondary"] {
    background: #e9f3ec !important;
    color: #1a4731 !important;
    border: 1px solid #9ec5ab !important;
}

/* Keep sidebar reset button style stable (override global secondary rule) */
[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.15) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: #f3f9f4 !important;
    border: 1px solid #b7d3be !important;
}
</style>
""", unsafe_allow_html=True)

# ── Helper functions ───────────────────────────────────────────────────────────

def fmt_twd(n):
    """Format number as TWD with commas."""
    if n is None:
        return "–"
    return f"NT$ {int(n):,}"

def get_alert_level(budget):
    """Return alert level info dict based on total project budget.
    此燈號依「計畫總經費」判定，反映計畫的隱含碳潛力與應投入的檢核力道，
    與「氣候預算金額」（實際投入的氣候相關經費）為不同概念。
    """
    if budget >= PARAMS["extreme_alert_threshold"]:
        return {"level": "extreme", "label": "⛔ 氣候預算潛力：城市重塑", "desc": "依計畫總經費判定；屬重大公共建設，強烈建議淨零檢核",
                "color": "#8e44ad", "badge": "🟣"}
    elif budget >= PARAMS["high_alert_threshold"]:
        return {"level": "red", "label": "🔴 氣候預算潛力：部門轉型", "desc": "依計畫總經費判定；金額≥2000萬，強調隱含碳檢核",
                "color": "#e74c3c", "badge": "🔴"}
    elif budget >= PARAMS["medium_alert_threshold"]:
        return {"level": "yellow", "label": "🟡 氣候預算潛力：效能升級", "desc": "依計畫總經費判定；金額1000萬–2000萬",
                "color": "#f39c12", "badge": "🟡"}
    else:
        return {"level": "green", "label": "🟢 氣候預算潛力：基層守護", "desc": "依計畫總經費判定；金額300萬–1000萬",
                "color": "#2ecc71", "badge": "🟢"}

def detect_keywords(text):
    """Return list of matching keyword triggers from case name."""
    if not text:
        return []
    matches = []
    seen = set()
    for kw in KWDICT["keyword_triggers"]:
        keyword = kw.get("keyword", "")
        if not keyword or keyword in seen:
            continue
        synonyms = kw.get("synonyms", [])
        candidates = [keyword] + [s for s in synonyms if s]
        matched_term = next((c for c in candidates if c in text), "")
        if not matched_term:
            continue
        negative_context = kw.get("negative_context", [])
        if any(ctx in text for ctx in negative_context):
            continue
        hit = dict(kw)
        hit["matched_term"] = matched_term
        hit.setdefault("match_type", "strong_trigger")
        matches.append(hit)
        seen.add(keyword)

    for rule in KWDICT.get("keyword_logic", []):
        triggers = rule.get("triggers", [])
        if not triggers:
            continue
        synthetic_keyword = "/".join(triggers)
        # Multi-trigger logic rules should match only when all triggers appear.
        if all(t in text for t in triggers) and synthetic_keyword not in seen:
            matches.append({
                "keyword": synthetic_keyword,
                "suggested_item": rule.get("suggested_item", ""),
                "code": "logic",
                "category_id": rule.get("category_id", ""),
                "sub_id": rule.get("sub_id", ""),
                "note": rule.get("note", ""),
                "_match_type": "logic",  # 標記為邏輯組合規則
            })
            seen.add(synthetic_keyword)
    return matches

def split_keyword_matches(kw_matches):
    """Split matches into strong/concept/logic buckets for layered guidance."""
    strong, concept, logic = [], [], []
    for kw in kw_matches:
        if kw.get("_match_type") == "logic":
            logic.append(kw)
            continue
        if kw.get("match_type", "strong_trigger") == "concept_trigger":
            concept.append(kw)
        else:
            strong.append(kw)
    return strong, concept, logic


def anti_pattern_check(case_name: str, selected_items: list[dict]) -> list[dict]:
    """
    Phase 1A 骨幹：根據標案名稱與已選工項，檢查是否命中反例提示規則。

    讀取 CONFIG["anti_patterns"]，回傳命中的規則清單。
    Phase 1B 會在 Step 2 / Step 3 呼叫此函式，並將結果寫入
    st.session_state["anti_pattern_hits"]。

    回傳格式：list[dict]，每筆包含：
      {id, name, severity, action_type, warning_text, trigger_matched, exclude_matched}

    觸發邏輯（依 JSON 定義）：
      trigger_keywords        : any/all（由 require_all_triggers 決定）
      require_context_keywords: 若存在，需同時包含至少一個上下文詞彙
      require_any_context     : 同上（舊欄位名，向下相容）
      exclude_keywords        : 出現則不觸發

    AP10 特殊說明：trigger=[工程/施工], exclude=[勞安/高溫/...], require_all=True
                  此組合已足夠，不需額外程式分支。
    """
    hits: list[dict] = []
    text = case_name.strip()

    for ap in CONFIG.get("anti_patterns", []):
        ap_id       = ap["id"]
        triggers    = ap.get("trigger_keywords", [])
        excludes    = ap.get("exclude_keywords", [])
        require_all = ap.get("require_all_triggers", False)
        # 支援兩種上下文欄位名稱（向下相容）
        require_ctx = ap.get("require_context_keywords",
                             ap.get("require_any_context", []))

        # ── 觸發條件 ──────────────────────────────────────────────────
        if require_all:
            trigger_matched = all(t in text for t in triggers)
        else:
            trigger_matched = any(t in text for t in triggers)

        if not trigger_matched:
            continue

        # ── 上下文條件（若設定）──────────────────────────────────────
        if require_ctx and not any(c in text for c in require_ctx):
            continue

        # ── 排除條件 ──────────────────────────────────────────────────
        if any(e in text for e in excludes):
            continue

        hits.append({
            "id":            ap_id,
            "name":          ap.get("name", ""),
            "severity":      ap.get("severity", "caution"),
            "action_type":   ap.get("action_type", "remind"),
            "warning_text":  ap.get("warning_text", ""),
            "default_purity": ap.get("default_purity", "P3_PARTIAL"),
            "trigger_matched_keywords": [t for t in triggers if t in text],
        })

    return hits


def anti_pattern_check_items(item_budgets: list[dict]) -> list[dict]:
    """
    工項層級的反例提示檢查（補充 anti_pattern_check 的 case_name 層級）。

    讀取每個工項的 anti_pattern_ref，回傳命中的 anti_pattern 規則。
    Phase 1B 在 Step 3 工項選擇完成後呼叫。
    """
    hit_ids: set[int] = set()
    for ib in item_budgets:
        for ap_id in ib.get("anti_pattern_ref", []):
            hit_ids.add(ap_id)

    hits: list[dict] = []
    for ap_id in sorted(hit_ids):
        ap = ANTI_PATTERNS.get(ap_id)
        if ap:
            hits.append({
                "id":           ap_id,
                "name":         ap.get("name", ""),
                "severity":     ap.get("severity", "caution"),
                "action_type":  ap.get("action_type", "remind"),
                "warning_text": ap.get("warning_text", ""),
                "default_purity": ap.get("default_purity", "P3_PARTIAL"),
                "source":       "item_ref",   # 區分來源：case_name vs item
            })
    return hits


def merge_anti_pattern_hits(
    case_hits: list[dict],
    item_hits: list[dict],
) -> list[dict]:
    """
    合併 case_name 層級與工項層級的反例命中，去除重複（以 id 去重）。
    優先保留 case_name 層級（包含 trigger_matched_keywords 資訊）。
    """
    seen: set[int] = set()
    merged: list[dict] = []
    for h in case_hits + item_hits:
        if h["id"] not in seen:
            seen.add(h["id"])
            merged.append(h)
    return merged


def compute_confidence(kw_matches, manual_override, budget, selected_items):
    """
    計算判讀信心等級。
    回傳 dict: { level: "high"/"medium"/"low", label: str, badge_html: str, reasons: list[str] }
    """
    forced_review_threshold = CONFIG.get("weighting_parameters", {}).get(
        "high_budget_forced_review_threshold", 50000000
    )
    strong_matches, concept_matches, logic_matches = split_keyword_matches(kw_matches)

    reasons = []

    if manual_override:
        level = "low"
        reasons.append("使用者啟用「人工覆核模式」（未達門檻仍繼續評估）")
    elif not kw_matches and not selected_items:
        level = "low"
        reasons.append("未命中任何關鍵字，工項全部為人工選擇")
    elif not kw_matches and selected_items:
        level = "low"
        reasons.append("未命中任何關鍵字，工項依人工判斷填入")
    elif len(strong_matches) >= 2:
        level = "high"
        kw_list = "、".join(f"「{kw['keyword']}」" for kw in strong_matches[:4])
        reasons.append(f"命中 {len(strong_matches)} 個強觸發關鍵字：{kw_list}")
        if concept_matches:
            reasons.append(f"另命中 {len(concept_matches)} 個概念提示詞（需後續確認）")
        if logic_matches:
            reasons.append(f"另命中 {len(logic_matches)} 個組合條件規則")
    elif len(strong_matches) == 1:
        level = "medium"
        reasons.append(f"命中 1 個關鍵字：「{strong_matches[0]['keyword']}」，建議人工確認工項是否完整")
        if concept_matches:
            reasons.append(f"另命中 {len(concept_matches)} 個概念提示詞（相關但未確定）")
    elif logic_matches:
        level = "medium"
        kw_list = "、".join(f"「{kw['keyword']}」" for kw in logic_matches[:3])
        reasons.append(f"命中 {len(logic_matches)} 個組合條件規則：{kw_list}")
    elif concept_matches:
        level = "medium"
        kw_list = "、".join(f"「{kw['keyword']}」" for kw in concept_matches[:4])
        reasons.append(f"命中 {len(concept_matches)} 個概念提示詞：{kw_list}")
        reasons.append("目前僅判定為『與氣候相關』，請下一步確認減緩/調適與具體工項")
    else:
        level = "low"
        reasons.append("未命中任何關鍵字，全部依人工選擇")

    if budget >= forced_review_threshold and not kw_matches:
        reasons.append(f"⚠️ 金額 ≥ {forced_review_threshold:,} 元且無關鍵字命中，已強制進入人工檢核")
        if level == "high":
            level = "medium"

    labels = {"high": "🟢 高信心", "medium": "🟡 中信心", "low": "🔴 低信心"}
    badges = {
        "high":   '<span class="confidence-high">🟢 高信心</span>',
        "medium": '<span class="confidence-medium">🟡 中信心</span>',
        "low":    '<span class="confidence-low">🔴 低信心</span>',
    }
    descs = {
        "high":   "關鍵字命中充分，判讀結果可信度高",
        "medium": "部分命中，建議人工確認工項與類別",
        "low":    "無關鍵字佐證，全部依人工選擇，建議加強說明",
    }
    return {
        "level":      level,
        "label":      labels[level],
        "badge_html": badges[level],
        "desc":       descs[level],
        "reasons":    reasons,
    }


def compute_reduction_completeness(item_budgets, physical_reductions):
    """
    工程減量資訊完整度。
    只在有勾選「純零成本」或「量體減量觸發」工項時才回傳結果，否則回傳 None（不顯示）。

    回傳 dict 或 None:
    {
        level: "high" / "medium" / "low",
        label: str,
        badge_html: str,
        filled_count: int,   # 4 格中填了幾格
        reasons: list[str],
    }
    """
    # 判斷是否有任何減量相關工項被勾選
    has_reduction_item = any(
        is_pure_zero_cost(ib.get("label", "")) or is_smart_use_item(ib.get("label", ""))
        or any(trigger in ib.get("label", "") for trigger in PHYSICAL_REDUCTION_TRIGGERS)
        for ib in item_budgets
    )

    if not has_reduction_item:
        return None   # 無減量工項，不顯示此指標

    # 計算 4 個效益欄位中填了幾格
    phys = physical_reductions or {}
    filled = 0
    details = []

    if phys.get("soil_reduction_ton", 0):
        filled += 1
        details.append(f"已填：減少土方購置 {phys['soil_reduction_ton']} 公噸")
    if phys.get("waste_reduction_ton", 0):
        filled += 1
        details.append(f"已填：減少廢棄物外運 {phys['waste_reduction_ton']} 公噸")
    if phys.get("cement_reduction_ton", 0):
        filled += 1
        details.append(f"已填：減少水泥等建材 {phys['cement_reduction_ton']} 公噸")
    if phys.get("other_benefit_note", "").strip():
        filled += 1
        details.append("已填：其他效益說明")

    # 判定等級
    if filled >= 1:
        level = "high"
        reasons = details + ["✅ 已提供工程減量佐證資料"]
    else:
        level = "low"
        reasons = ["⚠️ 已勾選工程減量工項，但「工程量體縮減及其他效益」區塊尚未填寫任何資料",
                   "建議返回步驟四，填寫至少一項效益估算或說明"]

    labels = {"high": "🟢 完整", "low": "🔴 待補充"}
    badges = {
        "high": '<span class="confidence-high">🟢 完整</span>',
        "low":  '<span class="confidence-low">🔴 待補充</span>',
    }
    descs = {
        "high": f"已提供 {filled}/4 項效益佐證資料",
        "low":  "已勾選減量工項但尚未填寫任何效益資料",
    }
    return {
        "level":        level,
        "label":        labels[level],
        "badge_html":   badges[level],
        "filled_count": filled,
        "desc":         descs[level],
        "reasons":      reasons,
    }


def build_explain_html(kw_matches, manual_override, budget):
    """
    組裝「判讀理由面板」的 HTML 字串，供 Step 1/Step 4 顯示。
    """
    forced_review_threshold = CONFIG.get("weighting_parameters", {}).get(
        "high_budget_forced_review_threshold", 50000000
    )

    if not kw_matches and not manual_override and budget < forced_review_threshold:
        return ""

    rows_html = ""

    if kw_matches:
        for kw in kw_matches:
            match_type = kw.get("_match_type", "exact")
            if match_type == "logic":
                type_badge = '<span class="explain-type-logic">組合條件</span>'
                triggers = kw["keyword"].split("/")
                kw_display = " ＋ ".join(f"「{t}」" for t in triggers)
            elif kw.get("match_type", "strong_trigger") == "concept_trigger":
                type_badge = '<span class="explain-type-manual">概念提示</span>'
                kw_display = f"「{kw['keyword']}」"
            else:
                type_badge = '<span class="explain-type-strong">強觸發</span>'
                kw_display = f"「{kw['keyword']}」"

            cat_obj  = get_taxonomy_by_id(kw.get("category_id", ""))
            cat_name = f"{cat_obj['icon']} {cat_obj['label']}" if cat_obj else kw.get("category_id", "–")
            note_txt = f"｜{kw['note']}" if kw.get("note") else ""

            rows_html += (
                f'<div class="explain-row">'
                f'🔑 關鍵字 {kw_display}{type_badge}'
                f' → <b>{kw["suggested_item"]}</b>'
                f' ／ 類別：{cat_name}{note_txt}'
                f'</div>'
            )
    else:
        rows_html += '<div class="explain-row">未偵測到任何關鍵字</div>'

    if manual_override:
        rows_html += '<div class="explain-row">⚠️ 使用者啟用人工覆核模式（手動繼續評估） <span class="explain-type-manual">人工覆核</span></div>'

    if budget >= forced_review_threshold and not kw_matches:
        rows_html += (
            f'<div class="explain-row">🔴 金額 {budget:,} 元 ≥ {forced_review_threshold:,} 元 且無關鍵字命中，系統強制觸發人工檢核'
            f' <span class="explain-type-budget">金額強制</span></div>'
        )

    return (
        f'<div class="explain-panel">'
        f'<div class="explain-title">🔍 判讀依據說明</div>'
        f'{rows_html}'
        f'</div>'
    )

def detect_text_keywords(text, keywords):
    """Return matched keywords contained in text."""
    if not text:
        return []
    return [k for k in keywords if k and k in text]



def get_taxonomy_by_id(cat_id):
    for cat in LOGIC["taxonomy"]:
        if cat["id"] == cat_id:
            return cat
    return None

def get_taxonomies_by_ids(cat_ids):
    return [cat for cat_id in cat_ids if (cat := get_taxonomy_by_id(cat_id))]

def get_sub_by_id(cat, sub_id):
    for sub in cat.get("sub_categories", []):
        if sub["id"] == sub_id:
            return sub
    return None

def get_sub_by_id_global(sub_id):
    for cat in LOGIC["taxonomy"]:
        sub = get_sub_by_id(cat, sub_id)
        if sub:
            return cat, sub
    return None, None

def get_available_sub_entries(selected_categories):
    """回傳已選類別下所有啟用中的細項（enabled != False 才顯示）。"""
    entries = []
    for cat in get_taxonomies_by_ids(selected_categories):
        for sub in cat.get("sub_categories", []):
            if sub.get("enabled", True) is False:
                continue  # 已關閉的細項（如 C3 軌道鐵道）不顯示於 UI
            entries.append({"category": cat, "sub": sub})
    return entries

def get_item_sources(selected_categories, selected_sub_categories):
    """回傳工項來源清單。
    - 正常細項：直接取該細項工項。
    - _NONE 虛擬細項（使用者選「不確定適合項目」）：展開對應類別全部啟用細項。
    - 同樣排除 enabled=False 的細項。
    """
    if selected_sub_categories:
        sources = []
        seen_sub_ids = set()
        for sub_id in selected_sub_categories:
            if sub_id.endswith("_NONE"):
                # 逃生出口：展開該 cat 底下所有啟用細項
                cat_id = sub_id.replace("_NONE", "")
                cat = get_taxonomy_by_id(cat_id)
                if cat:
                    for sub in cat.get("sub_categories", []):
                        if sub.get("enabled", True) is False:
                            continue
                        if sub["id"] not in seen_sub_ids:
                            seen_sub_ids.add(sub["id"])
                            sources.append({"category": cat, "sub": sub})
            else:
                cat, sub = get_sub_by_id_global(sub_id)
                if cat and sub and sub.get("enabled", True) is not False:
                    if sub["id"] not in seen_sub_ids:
                        seen_sub_ids.add(sub["id"])
                        sources.append({"category": cat, "sub": sub})
        return sources
    return get_available_sub_entries(selected_categories)

def get_available_item_labels(selected_categories, selected_sub_categories):
    labels = set()
    for entry in get_item_sources(selected_categories, selected_sub_categories):
        for item in entry["sub"].get("items", []):
            labels.add(item["label"])
    return labels

def prune_invalid_selections(selected_items, item_budgets, valid_labels):
    valid_item_budgets = [ib for ib in item_budgets if ib.get("label") in valid_labels]
    valid_selected_items = [label for label in selected_items if label in valid_labels]
    removed_labels = [
        label for label in selected_items
        if label not in valid_labels
    ]
    return valid_selected_items, valid_item_budgets, removed_labels

def format_category_labels(category_ids):
    return "、".join(
        cat["label"] for cat in get_taxonomies_by_ids(category_ids)
    )

def format_sub_category_labels(sub_ids):
    labels = []
    for sub_id in sub_ids:
        _, sub = get_sub_by_id_global(sub_id)
        if sub:
            labels.append(sub["label"])
    return "、".join(labels)

def get_item_by_label(sub, label):
    """Look up an item by label within a single sub-category dict."""
    for item in sub.get("items", []):
        if item.get("label") == label:
            return item
    return None

def safe_key(text):
    """Hash arbitrary text to a short, collision-free, alphanumeric Streamlit widget key."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

def inject_button_style(key, *, is_selected=False, is_suggested=False):
    """Inject CSS so specific Streamlit buttons can visually reflect state."""
    if is_selected:
        bg = "#2d6a4f"
        text = "#ffffff"
        border = "#2d6a4f"
        shadow = "0 4px 16px rgba(45,106,79,0.18)"
    elif is_suggested:
        bg = "#fffbf0"
        text = "#8f5c00"
        border = "#f39c12"
        shadow = "0 4px 16px rgba(243,156,18,0.2)"
    else:
        bg = "#e9f3ec"
        text = "#1a4731"
        border = "#9ec5ab"
        shadow = "none"

    if is_selected:
        hover_border = border
        hover_bg = bg
    else:
        hover_border = "#2d6a4f" if not is_suggested else "#f39c12"
        hover_bg = "#f0f9f0" if not is_suggested else "#fff6dd"

    st.markdown(
        f"""
        <style>
        .st-key-{key} button {{
            background: {bg} !important;
            color: {text} !important;
            border: 1px solid {border} !important;
            box-shadow: {shadow} !important;
            min-height: 3rem;
            white-space: normal;
        }}
        .st-key-{key} button:hover {{
            border-color: {hover_border} !important;
            background: {hover_bg} !important;
            color: {text} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── 「純零成本」工項清單（部分比對）──────────────────────────────────
# 這類工項是施工決策或現場再利用，本身不產生採購費用。
# 步驟四不顯示金額輸入，改為引導填寫量體效益欄位。
PURE_ZERO_COST_KEYWORDS = [
    "現地土方平衡",
    "瀝青刨除料",
    "路堤回填採用瀝青刨除料",
    "道碴碎石",
    "廢水污泥再利用",
    "焚化底渣",
    "有機廢棄物現地堆肥化",
]

# ── 「聰明使用型」工項清單（部分比對）────────────────────────────────
# 這類工項有採購行為（如 CLSM、循環建材、模組化預鑄），經費仍可填寫，
# 但允許填 0，並加註提示引導填寫量體效益欄位。
SMART_USE_KEYWORDS = [
    "應用再生粒料",
    "導入低蘊含碳建材或循環建材",
    "模組化預鑄構件",
    "地工合成加勁材擋土牆",
    "資源回收再生系統",
]

def is_pure_zero_cost(label: str) -> bool:
    """純零成本：施工決策/現場再利用，不產生採購費用。"""
    return any(kw in label for kw in PURE_ZERO_COST_KEYWORDS)

def is_smart_use_item(label: str) -> bool:
    """聰明使用型：有採購行為但具量體減量效益，經費可填也可填 0。"""
    return any(kw in label for kw in SMART_USE_KEYWORDS)

def is_zero_cost_item(label: str) -> bool:
    """向下相容：純零成本 OR 聰明使用型，皆屬廣義「減量工項」。"""
    return is_pure_zero_cost(label) or is_smart_use_item(label)

HEAT_SAFETY_KEYWORDS = [
    "工程", "施工", "改善", "新建", "修復", "整修",
    "道路", "排水", "管線", "河川", "水環境",
]
HEAT_SAFETY_EXCLUDE_KEYWORDS = ["委託", "規劃", "研究", "監測系統"]
ENGINEERING_MAIN_CATEGORY_IDS = {"A", "B", "C", "D", "E"}

def should_trigger_heat_safety_prompt(project_name, category_ids, department):
    """
    判斷是否觸發高溫作業調適提醒（最小可用版）。
    規則：
      1) 主類別含工程類（A/B/C/D/E）即觸發
      2) 或標案名稱含工程關鍵字即觸發
    """
    cat_ids = set(category_ids or [])
    if cat_ids & ENGINEERING_MAIN_CATEGORY_IDS:
        return True

    project_text = str(project_name or "")
    if any(kw in project_text for kw in HEAT_SAFETY_EXCLUDE_KEYWORDS):
        return False

    return any(kw in project_text for kw in HEAT_SAFETY_KEYWORDS)

# ── 工項 → 量體縮減欄位觸發對應表 ──────────────────────────────────────────
# key: 工項 label（部分比對）, value: 觸發哪些量體縮減欄位
# 欄位: soil_reduction_ton（減少土方購置, 公噸）, waste_reduction_ton（減少廢棄物外運, 公噸）
PHYSICAL_REDUCTION_TRIGGERS = {
    # 土方平衡 → 兩者都可能
    "現地土方平衡": ["soil_reduction_ton", "waste_reduction_ton"],
    # RAP 刨除料再利用 → 減少廢棄物外運
    "瀝青刨除料": ["waste_reduction_ton"],
    "路堤回填採用瀝青刨除料": ["waste_reduction_ton"],
    "道碴碎石": ["waste_reduction_ton"],
    # 污泥、廢水再利用 → 減少廢棄物外運
    "廢水污泥再利用": ["waste_reduction_ton"],
    "焚化底渣": ["waste_reduction_ton"],
    # 循環建材 → 減少廢棄物外運
    "導入低蘊含碳建材或循環建材": ["waste_reduction_ton"],
    "模組化預鑄構件": ["waste_reduction_ton"],
    # 加勁擋土牆（取代混凝土）→ 減少廢棄物外運（少用混凝土）
    "地工合成加勁材擋土牆": ["waste_reduction_ton"],
    # 堆肥化
    "有機廢棄物現地堆肥化": ["waste_reduction_ton"],
    # 再生粒料
    "應用再生粒料": ["waste_reduction_ton"],
}

def get_physical_reduction_fields(item_budgets):
    """依已選工項，回傳需顯示的量體縮減欄位集合。"""
    fields = set()
    for ib in item_budgets:
        label = ib.get("label", "")
        for trigger, trigger_fields in PHYSICAL_REDUCTION_TRIGGERS.items():
            if trigger in label:
                fields.update(trigger_fields)
    return fields


def generate_uid(case_name=""):
    """Generate unique case ID with timestamp-seconds + name-hash + random suffix."""
    ts   = datetime.now(tz=TZ_TAIPEI).strftime("%Y%m%d%H%M%S")
    name_hash = hashlib.md5(case_name.encode("utf-8")).hexdigest()[:4].upper() if case_name else "XXXX"
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"CHC-{ts}-{name_hash}-{rand_part}"


def generate_export_json(state):
    """
    生成匯出 JSON（Phase 1A 結構升級）。

    明確分成兩大區塊：
      budget_summary         — 計算資料（金額、占比、列入計算的工項）
      interpretation_summary — 解讀資料（相關性標記、非預算型效益、anti_pattern命中）

    金額計算只看 count_in_budget_total=True 的工項；
    解讀資料不影響任何數字，僅供摘要與人工判讀使用。
    """
    selected_categories     = state.get("selected_categories", [])
    selected_sub_categories = state.get("selected_sub_categories", [])
    item_budgets            = state.get("item_budgets", [])
    kw_matches              = state.get("kw_matches", [])
    manual_override         = state.get("manual_override", False)
    budget                  = state.get("budget", 0)
    heat_safety_prompt_triggered = state.get("heat_safety_prompt_triggered", False)
    heat_safety_response = state.get("heat_safety_response", "")
    heat_safety_note = state.get("heat_safety_note", "")

    confidence = compute_confidence(kw_matches, manual_override, budget, item_budgets)

    # 分離預算型 vs 非預算型工項
    # count_in_budget_total 在 Phase 1B Step 3 UI 寫入 item_budgets；
    # 此前預設 True（向下相容舊資料）
    budget_items     = [ib for ib in item_budgets if ib.get("count_in_budget_total", True)]
    non_budget_items = [ib for ib in item_budgets if not ib.get("count_in_budget_total", True)]

    # 氣候預算總額（只加 budget 型）
    climate_total = sum(i.get("amount", 0) for i in budget_items)
    climate_ratio = round(climate_total / budget * 100, 1) if budget else 0.0

    # 工項相關性摘要文字
    item_relevance_parts = []
    for ib in budget_items:
        purity_code = ib.get("purity", "")
        p_label = purity_label(purity_code) if purity_code else ""
        label = ib.get("label", "")
        if label:
            item_relevance_parts.append(
                f"{label}（{p_label}）" if p_label else label
            )
    item_relevance_text = "、".join(item_relevance_parts)

    # 非預算型效益說明文字
    non_budget_parts = []
    for ib in non_budget_items:
        btype = ib.get("benefit_type", "")
        label = ib.get("label", "")
        note  = ib.get("note", "")
        type_label = {"design": "設計型", "management": "管理型"}.get(btype, btype)
        entry = f"【{type_label}】{label}"
        if note:
            entry += f"：{note}"
        non_budget_parts.append(entry)
    non_budget_text = "；".join(non_budget_parts)

    # anti_pattern 命中記錄（Phase 1B 由 anti_pattern_check() 寫入 state）
    ap_hits = state.get("anti_pattern_hits", [])
    ap_hits_text = "、".join(
        f"AP{h['id']}:{h.get('name', '')}" for h in ap_hits
    ) if ap_hits else ""

    result = {
        # ── 專案基本資訊 ──────────────────────────────────────────────────
        "project_metadata": {
            "uid":               generate_uid(state.get("case_name", "")),
            "name":              state.get("case_name", ""),
            "dept":              state.get("dept", ""),
            "total_budget":      budget,
            "is_manual_override": manual_override,
            "assessment_date":   datetime.now(tz=TZ_TAIPEI).strftime("%Y-%m-%d %H:%M"),
            "rule_versions": {
                "config_version": CONFIG_VERSION,
                "data_version":   DATA_VERSION,
                "kd_version":     KD_VERSION,
                "lm_version":     LM_VERSION,
            },
        },

        # ── 計算資料（budget_summary）──────────────────────────────────────
        "budget_summary": {
            "climate_budget_total": climate_total,
            "climate_budget_ratio": climate_ratio,
            "alert_level":          get_alert_level(budget)["label"],
            "counted_items": [
                {
                    "label":        ib.get("label", ""),
                    "amount":       ib.get("amount", 0),
                    "ratio":        ib.get("ratio", 0.0),
                    "item_id":      ib.get("item_id", ""),
                    "is_zero_cost": ib.get("is_zero_cost", False),
                    "is_smart_use": ib.get("is_smart_use", False),
                }
                for ib in budget_items
            ],
            "categories":          selected_categories,
            "category_labels":     format_category_labels(selected_categories),
            "sub_categories":      selected_sub_categories,
            "sub_category_labels": format_sub_category_labels(selected_sub_categories),
        },

        # ── 解讀資料（interpretation_summary）─────────────────────────────
        "interpretation_summary": {
            "item_relevance_text":     item_relevance_text,
            "item_relevance_detail": [
                {
                    "label":        ib.get("label", ""),
                    "item_id":      ib.get("item_id", ""),
                    "purity_code":  ib.get("purity", ""),
                    "purity_label": purity_label(ib.get("purity", "")),
                }
                for ib in budget_items
            ],
            "non_budget_benefits":      non_budget_text,
            "non_budget_items_detail": [
                {
                    "label":        ib.get("label", ""),
                    "item_id":      ib.get("item_id", ""),
                    "benefit_type": ib.get("benefit_type", ""),
                    "note":         ib.get("note", ""),
                }
                for ib in non_budget_items
            ],
            "anti_pattern_hits":       ap_hits,
            "anti_pattern_hits_text":  ap_hits_text,
            "has_low_relevance_items": any(
                ib.get("purity") in ("P4_LOW", "P5_MANAGEMENT") for ib in budget_items
            ),
        },

        # ── 判讀品質 ──────────────────────────────────────────────────────
        "confidence": {
            "level":   confidence["level"],
            "label":   confidence["label"],
            "desc":    confidence["desc"],
            "reasons": confidence["reasons"],
        },
        "matched_keywords": [kw["keyword"] for kw in kw_matches],
        "matched_trigger_ids": [
            kw.get("trigger_id", "") for kw in kw_matches if kw.get("trigger_id")
        ],

        # ── 量體縮減 ──────────────────────────────────────────────────────
        "physical_reductions": state.get("physical_reductions", {}),
        "reduction_completeness": (lambda rc: {
            "level":        rc["level"],
            "label":        rc["label"],
            "filled_count": rc["filled_count"],
            "desc":         rc["desc"],
        } if rc else None)(
            compute_reduction_completeness(
                item_budgets, state.get("physical_reductions", {})
            )
        ),

        # ── 舊版相容欄位（Phase 2 重構前保留）────────────────────────────
        "climate_budget_total": climate_total,
        "climate_assessment": {
            "categories":          selected_categories,
            "category_labels":     format_category_labels(selected_categories),
            "sub_categories":      selected_sub_categories,
            "sub_category_labels": format_sub_category_labels(selected_sub_categories),
            "selected_items": [
                {**ib, "is_zero_cost": ib.get("is_zero_cost", False)}
                for ib in item_budgets
            ],
            "alert_level": get_alert_level(budget)["label"],
        },
        "impact_level": get_alert_level(budget)["level"],

        # ── 評估 metadata ─────────────────────────────────────────────────
        "assessment_metadata": {
            "engineering_guideline_type": state.get("engineering_guideline_type", ""),
            "user_note":     state.get("user_note", ""),
            "management_adaptation_prompt": {
                "triggered": heat_safety_prompt_triggered,
                "response": heat_safety_response,
                "note": heat_safety_note,
            },
            "preset_reference": state.get("preset_reference", {}),
            "system_version": "1.2",
        },
    }
    return result


def get_google_sheet_webhook_url():
    """Get Google Sheet webhook URL from Streamlit secrets or config."""
    candidate_keys = [
        "google_sheet_webhook_url",
        "google_sheet_webhook",
        "google_sheet_sync_url",
        "google_sheet_url",
    ]

    for key in candidate_keys:
        secret_url = st.secrets.get(key)
        if secret_url is not None:
            normalized_secret_url = str(secret_url).strip()
            if normalized_secret_url:
                return normalized_secret_url

    integrations = CONFIG.get("integrations", {})
    for key in candidate_keys:
        config_url = integrations.get(key)
        if config_url is not None:
            normalized_config_url = str(config_url).strip()
            if normalized_config_url:
                return normalized_config_url

    return ""


def get_google_sheet_target():
    """Get default Google Sheet target settings."""
    return {
        "spreadsheet_id": st.secrets.get("google_sheet_id")
        or CONFIG.get("integrations", {}).get("google_sheet_id", ""),
        "worksheet_name": st.secrets.get("google_sheet_worksheet")
        or CONFIG.get("integrations", {}).get("google_sheet_worksheet", "工作表1"),
    }


def get_department_options() -> list[str]:
    """回傳局處清單（供 Step 0 下拉選單使用）。"""
    configured_departments = CONFIG.get("departments", [])
    return configured_departments if isinstance(configured_departments, list) else []


def get_dept_preset(dept_name: str) -> dict:
    """
    查詢局處預設設定。

    回傳 department_presets[dept_name]，找不到時回傳空 dict。
    主要欄位：
      default_categories     : list[str]  主推薦類別（依 category_priority_order 排序）
      category_priority_order: list[str]  完整優先序
      default_hint_mode      : str        提示模式
      dept_hint              : str        UI 提示文字
      common_anti_pattern_ids: list[int]  此局處常見的 anti_pattern
    """
    return DEPT_PRESETS.get(dept_name, {})


def apply_dept_preset(dept_name: str) -> None:
    """
    Phase 1B 骨幹：用戶選完局處後呼叫，將預設類別與提示文字寫入 session_state。

    Phase 1A 已預留 state key（dept_suggested_categories / dept_hint），
    Phase 1B Step 0 UI 完成後正式啟用此函式。
    """
    preset = get_dept_preset(dept_name)
    if not preset:
        st.session_state["dept_suggested_categories"] = []
        st.session_state["dept_hint"] = ""
        return

    # 依 category_priority_order 排序推薦類別
    priority_order = preset.get("category_priority_order",
                                preset.get("default_categories", []))
    st.session_state["dept_suggested_categories"] = priority_order
    st.session_state["dept_hint"] = preset.get("dept_hint", "")


def is_sheet_sync_ready():
    """Return whether either webhook sync or direct Sheets API sync is available."""
    if get_google_sheet_webhook_url():
        return True

    has_service_account = bool(st.secrets.get("gcp_service_account"))
    has_sheet_id = bool(get_google_sheet_target().get("spreadsheet_id"))
    return has_service_account and has_sheet_id


def get_google_sheet_client():
    """Create Google Sheets client from Streamlit secrets service account."""
    service_account_info = st.secrets.get("gcp_service_account")
    if not service_account_info:
        return None, "尚未設定 gcp_service_account（service account 金鑰）"

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        service_account_dict = dict(service_account_info)
    except Exception as e:
        return None, f"gcp_service_account 格式錯誤：{e}"

    try:
        creds = Credentials.from_service_account_info(
            service_account_dict,
            scopes=scopes,
        )
        return gspread.authorize(creds), ""
    except Exception as e:
        return None, f"service account 驗證失敗：{e}"


def resolve_header_key(col_name: str) -> str | None:
    """
    試算表欄位名稱 → 標準資料 key。

    比對順序（Phase 1A 強化版）：
      1. 精確相等：col_name == 標準 key
      2. alias 白名單精確比對：col_name == 某個 alias（完全相等）
      3. alias 白名單包含比對：alias in col_name（alias 是 col_name 的子字串）
         — 僅在步驟 1/2 都失敗時才嘗試，且同一 col_name 只能命中一個 key
         — 若多個 key 的 alias 都能匹配，視為不唯一，回傳 None 並記 log
      4. 找不到 → 回傳 None（該欄填空白）

    與舊版差異：
      - 舊版同時做「alias in col」和「col in alias」雙向包含，容易誤配
      - 新版只做單向（alias in col），且步驟 2 精確比對先行
      - 不唯一時明確拒絕（不猜），讓 unmatched_log 記錄供日後維護
    """
    col_stripped = col_name.strip()
    if not col_stripped:
        return None

    # 步驟 1：精確相等
    if col_stripped in HEADER_ALIAS_MAP:
        return col_stripped

    # 步驟 2：alias 白名單精確比對
    for std_key, aliases in HEADER_ALIAS_MAP.items():
        if col_stripped in aliases:
            return std_key

    # 步驟 3：alias 白名單包含比對（單向，不唯一時拒絕）
    candidates = []
    for std_key, aliases in HEADER_ALIAS_MAP.items():
        for alias in aliases:
            if alias in col_stripped:
                candidates.append(std_key)
                break  # 同一 std_key 只算一次

    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        # 不唯一：記錄但不配對
        import logging
        logging.warning(
            f"[resolve_header_key] 欄位「{col_stripped}」模糊比對到多個 key: "
            f"{candidates}，略過（填空白）"
        )
        return None

    return None


def build_sync_row_dict(payload):
    """
    從 export JSON payload 組出試算表列資料（以標準 header key 為 key）。

    Phase 1A 更新：
      - 從 budget_summary / interpretation_summary 讀取資料
      - 新增規則版本、工項相關性摘要、非預算型效益、anti_pattern命中欄位
      - 舊版相容：若 budget_summary 不存在，fallback 至舊結構
    """
    metadata  = payload.get("project_metadata", {})
    ameta     = payload.get("assessment_metadata", {})
    phys      = payload.get("physical_reductions", {})
    conf      = payload.get("confidence", {})

    # 優先從新結構讀取
    bs = payload.get("budget_summary", {})
    is_  = payload.get("interpretation_summary", {})

    # budget_summary fallback（向下相容舊格式）
    climate_total = bs.get("climate_budget_total") \
        if bs else payload.get("climate_budget_total", 0)
    total_budget  = metadata.get("total_budget", 0)
    climate_ratio = bs.get("climate_budget_ratio") \
        if bs else (round(climate_total / total_budget * 100, 1) if total_budget else 0)
    # 試算表欄位改為「百分比格式」時，需要傳入 0~1 的小數值（例如 41% → 0.41）
    climate_ratio_decimal = (
        round(float(climate_ratio) / 100, 6)
        if climate_ratio not in (None, "")
        else ""
    )

    # 工項文字
    if bs:
        items_text = "、".join(
            i.get("label", "") for i in bs.get("counted_items", []) if i.get("label")
        )
        cat_labels = bs.get("category_labels", "")
        sub_labels = bs.get("sub_category_labels", "")
    else:
        old_assessment = payload.get("climate_assessment", {})
        items_text = "、".join(
            i.get("label", "") for i in old_assessment.get("selected_items", [])
            if i.get("label")
        )
        cat_labels = old_assessment.get("category_labels", "")
        sub_labels = old_assessment.get("sub_category_labels", "")

    # 量體縮減摘要
    phys_parts = []
    if phys.get("soil_reduction_ton", 0):
        phys_parts.append(f"減少土方購置 {phys['soil_reduction_ton']} 公噸")
    if phys.get("waste_reduction_ton", 0):
        phys_parts.append(f"減少廢棄物外運 {phys['waste_reduction_ton']} 公噸")
    if phys.get("cement_reduction_ton", 0):
        phys_parts.append(f"減少水泥等建材 {phys['cement_reduction_ton']} 公噸")
    if phys.get("other_benefit_note", ""):
        phys_parts.append(phys["other_benefit_note"])
    phys_text = "；".join(phys_parts)

    # 規則版本字串
    rv = metadata.get("rule_versions", {})
    rule_ver_text = (
        f"config={rv.get('config_version','?')} "
        f"kd={rv.get('kd_version','?')} "
        f"lm={rv.get('lm_version','?')}"
    ) if rv else ""
    preset_ref = ameta.get("preset_reference", {}) or {}

    return {
        # ── 計算資料 ──────────────────────────────────────────────────
        "填報日期"          : datetime.now(tz=TZ_TAIPEI).strftime("%Y-%m-%d %H:%M:%S"),
        "案件編號"          : metadata.get("uid", ""),
        "標案名稱"          : metadata.get("name", ""),
        "主辦單位"          : metadata.get("dept", ""),
        "決標金額"          : total_budget,
        "氣候預算"          : climate_total,
        "氣候預算比例%"     : climate_ratio_decimal,
        "計畫類別"          : cat_labels,
        "細項分類"          : sub_labels,
        "氣候工項（預算型）": items_text,
        "關鍵字信心"        : conf.get("label", ""),
        "命中關鍵字"        : "、".join(payload.get("matched_keywords", [])),
        "規則版本"          : rule_ver_text,
        # ── 解讀資料 ──────────────────────────────────────────────────
        "工項相關性摘要"    : is_.get("item_relevance_text", "") if is_ else "",
        "非預算型效益"      : is_.get("non_budget_benefits", "") if is_ else "",
        "anti_pattern命中"  : is_.get("anti_pattern_hits_text", "") if is_ else "",
        "減量資訊完整度"    : (payload.get("reduction_completeness") or {}).get("label", ""),
        "工程量體縮減效益"  : phys_text,
        "國家關鍵戰略 (戰略層面 - Why)": preset_ref.get("national_strategy_why", ""),
        "計畫工法類別 (技術層面 - What)": preset_ref.get("methodology_what", ""),
        "氣候屬性 (功能層面 - How)": preset_ref.get("climate_attribute_how", ""),
        "潛在減緩/減碳亮點 (實務細節 - Action A)": preset_ref.get("mitigation_highlight_action_a", ""),
        "潛在調適/韌性亮點 (實務細節 - Action B)": preset_ref.get("adaptation_highlight_action_b", ""),
        "防呆提醒"          : preset_ref.get("foolproof_notice", ""),
        "補充說明"          : ameta.get("user_note", ""),
    }


def sync_to_google_sheet_direct(payload):
    """Append assessment payload directly to Google Sheets by service account.

    欄位對應邏輯：
    - 試算表第一列若已有表頭，以試算表欄位為準，依 resolve_header_key() 模糊比對填入。
    - 若試算表為空，自動寫入 DEFAULT_SYNC_HEADERS 作為表頭。
    - 試算表欄位無法比對時填入空字串，確保欄位順序不錯位。
    """
    client, err = get_google_sheet_client()
    if err:
        return False, err

    target = get_google_sheet_target()
    spreadsheet_id  = target.get("spreadsheet_id")
    worksheet_name  = target.get("worksheet_name") or "工作表1"
    if not spreadsheet_id:
        return False, "尚未設定 google_sheet_id"

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet   = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=30)
    except Exception as e:
        return False, f"無法連線試算表：{e}"

    # ── 取得現有表頭（第一列）
    try:
        first_row_values = [str(h).strip() for h in worksheet.row_values(1)]
        # 過濾尾端空欄
        while first_row_values and not first_row_values[-1]:
            first_row_values.pop()
    except Exception:
        first_row_values = []

    # ── 決定要使用的表頭
    if first_row_values:
        # 試算表已有表頭：沿用，不覆蓋
        headers = first_row_values
    else:
        # 試算表為空：寫入預設表頭
        headers = list(DEFAULT_SYNC_HEADERS)
        try:
            worksheet.update("A1", [headers])
        except Exception as e:
            return False, f"初始化試算表表頭失敗：{e}"

    # ── 組資料字典（以標準 key 為索引）
    row_dict = build_sync_row_dict(payload)

    # ── 依試算表表頭順序，模糊比對填入每欄值
    row = []
    for col_name in headers:
        std_key = resolve_header_key(col_name)
        row.append(row_dict.get(std_key, "") if std_key else "")

    # ── 寫入
    try:
        worksheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        return False, f"寫入試算表失敗：{e}"

    matched = sum(1 for col in headers if resolve_header_key(col))
    unmatched = [col for col in headers if not resolve_header_key(col)]
    msg = f"已寫入試算表 {spreadsheet_id}（{matched}/{len(headers)} 欄比對成功）"
    if unmatched:
        msg += f"，未比對欄位留空：{'、'.join(unmatched)}"
    return True, msg


@st.cache_data(ttl=600)
def load_registered_cases():
    """Load pre-registered case list from public Google Sheet."""
    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{PRESET_SHEET_ID}/"
        f"export?format=csv&gid={PRESET_SHEET_GID}"
    )

    req = request.Request(
        csv_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,text/plain,*/*",
        },
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8-sig", errors="ignore")
    except Exception as e:
        return pd.DataFrame(), f"無法讀取雲端試算表：{e}"

    try:
        df = pd.read_csv(io.StringIO(body)).fillna("")
    except Exception as e:
        return pd.DataFrame(), f"雲端試算表格式讀取失敗：{e}"

    if df.empty:
        return pd.DataFrame(), "雲端試算表沒有可用資料。"

    def pick_col(candidates):
        for col in df.columns:
            col_name = str(col).strip()
            if any(key in col_name for key in candidates):
                return col
        return None

    agency_col = pick_col(["機關"])
    unit_col = pick_col(["單位"])
    case_col = pick_col(["標案", "計畫名稱", "標的名稱"])
    budget_col = pick_col(["決標金額", "預算金額", "金額"])

    if not agency_col or not unit_col or not case_col:
        return pd.DataFrame(), "試算表缺少必要欄位（機關名稱、單位名稱、標案名稱）。"

    renamed = df.rename(
        columns={
            agency_col: "機關名稱",
            unit_col: "單位名稱",
            case_col: "標案名稱",
        }
    )
    if budget_col:
        renamed = renamed.rename(columns={budget_col: "決標金額"})
    else:
        renamed["決標金額"] = ""

    cleaned = renamed.copy()
    if "決標金額" not in cleaned.columns:
        cleaned["決標金額"] = ""
    for col in ["機關名稱", "單位名稱", "標案名稱"]:
        cleaned[col] = cleaned[col].astype(str).str.strip()
    cleaned = cleaned[(cleaned["機關名稱"] != "") & (cleaned["單位名稱"] != "") & (cleaned["標案名稱"] != "")]
    cleaned["_row_index"] = range(len(cleaned))
    cleaned["_budget_value"] = cleaned["決標金額"].apply(parse_budget_from_sheet)
    cleaned["_has_budget"] = cleaned["_budget_value"].gt(0)
    cleaned["_preset_ref_score"] = cleaned.apply(
        lambda row: sum(
            1 for v in extract_preset_reference(row).values()
            if str(v).strip()
        ),
        axis=1
    )
    cleaned = cleaned.sort_values(
        by=["_has_budget", "_preset_ref_score", "_budget_value", "_row_index"],
        ascending=[False, False, False, True]
    )
    cleaned = cleaned.drop_duplicates(subset=["機關名稱", "單位名稱", "標案名稱"], keep="first")
    cleaned = cleaned.drop(
        columns=["_preset_ref_score", "_has_budget", "_budget_value", "_row_index"],
        errors="ignore"
    )

    if cleaned.empty:
        return pd.DataFrame(), "試算表中沒有可用案件資料。"

    return cleaned.reset_index(drop=True), ""


def parse_budget_from_sheet(raw_value):
    """Safely parse budget value from sheet cell."""
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return 0

    if isinstance(raw_value, (int, float)):
        try:
            return max(int(float(raw_value)), 0)
        except (TypeError, ValueError):
            return 0

    raw_text = str(raw_value).strip().replace(",", "")
    if not raw_text:
        return 0

    try:
        return max(int(float(raw_text)), 0)
    except ValueError:
        return 0


def extract_preset_reference(raw_row: pd.Series | dict | None) -> dict:
    """從預載清單列資料萃取補充參考欄位。"""
    if raw_row is None:
        return {}

    row_data = raw_row.to_dict() if hasattr(raw_row, "to_dict") else dict(raw_row)
    normalized_cols = {
        normalize_text_key(col): col
        for col in row_data.keys()
    }

    extracted = {}
    for key, meta in PRESET_REFERENCE_COLUMNS.items():
        value = ""
        for pattern in meta.get("patterns", []):
            normalized_pattern = normalize_text_key(pattern)
            for normalized_col_name, original_col_name in normalized_cols.items():
                if normalized_pattern and normalized_pattern in normalized_col_name:
                    raw_value = row_data.get(original_col_name, "")
                    value = "" if raw_value is None else str(raw_value).strip()
                    break
            if value:
                break
        extracted[key] = value

    return extracted


def sync_to_google_sheet(payload):
    """Send assessment payload to Google Sheet webhook."""
    webhook_url = get_google_sheet_webhook_url()
    if not webhook_url:
        return sync_to_google_sheet_direct(payload)

    sync_payload = dict(payload)
    sync_payload["google_sheet_target"] = get_google_sheet_target()

    req = request.Request(
        webhook_url,
        data=json.dumps(sync_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            body = resp.read().decode("utf-8", errors="ignore")
            if 200 <= status_code < 300:
                return True, body or "同步成功"
            return False, f"同步失敗（HTTP {status_code}）：{body}"
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return False, f"同步失敗（HTTP {e.code}）：{body}"
    except error.URLError as e:
        return False, f"同步失敗（連線錯誤）：{e.reason}"

# ── Session state init ────────────────────────────────────────────────────────

def init_state():
    """
    初始化 session state。

    型別規範（Phase 1A 強化）：
      str   : case_name, dept, agency_name, unit_name, dept_other,
              engineering_guideline_type, user_note,
              sync_message, sync_signature, selection_warning,
              dept_hint,                 # Phase 1B：局處提示文字
              public_summary_text,       # Phase 1B：公文摘要
      int   : budget, step
      bool  : use_manual_case_input, manual_override, sync_done,
              negative_filter_override
      list  : kw_matches,               # list[dict]  每個 kw trigger dict
              selected_categories,      # list[str]   category id
              selected_sub_categories,  # list[str]   sub id
              selected_items,           # list[str]   item label
              item_budgets,             # list[dict]  {label, amount, ratio, ...}
              green_spending_category,  # list[str]
              qualitative_factors,      # list[str]
              anti_pattern_hits,        # list[dict]  Phase 1B anti_pattern_check 寫入
                                        #   每筆: {id, name, severity, action_type, warning_text}
              dept_suggested_categories, # list[str]  Phase 1B 局處預設推薦類別
      dict  : physical_reductions,      # {soil_reduction_ton, waste_reduction_ton, ...}
    """
    defaults: dict = {
        # ── 流程控制 ──────────────────────────────────────────────────
        "step":                     0,
        "max_unlocked_step":        0,
        "scroll_to_top":            False,
        # ── 案件基本資訊 ──────────────────────────────────────────────
        "case_name":                "",
        "dept":                     "",
        "agency_name":              "",
        "unit_name":                "",
        "dept_other":               "",
        "budget":                   0,
        "use_manual_case_input":    False,
        # ── 判讀狀態 ──────────────────────────────────────────────────
        "manual_override":          False,
        "kw_matches":               [],      # list[dict]
        "selected_categories":      [],      # list[str]
        "selected_sub_categories":  [],      # list[str]
        "selected_items":           [],      # list[str]
        "item_budgets":             [],      # list[dict]
        "engineering_guideline_type": "",
        "green_spending_category":  [],      # list[str]
        "qualitative_factors":      [],      # list[str]
        "physical_reductions":      {},      # dict
        "user_note":                "",
        "heat_safety_prompt_triggered": False,
        "heat_safety_response":     "",
        "heat_safety_note":         "",
        "selection_warning":        "",
        "negative_filter_override": False,
        # ── 同步狀態 ──────────────────────────────────────────────────
        "sync_done":                False,
        "sync_message":             "",
        "sync_signature":           "",
        # ── Phase 1A 新增：anti_pattern 命中記錄 ──────────────────────
        # list[dict]；每筆由 anti_pattern_check() 寫入
        # 格式：{id:int, name:str, severity:str, action_type:str, warning_text:str}
        "anti_pattern_hits":        [],      # list[dict]
        # ── Phase 1B 預留：局處預設 ───────────────────────────────────
        # 用戶選完局處後，由 apply_dept_preset() 寫入
        "dept_suggested_categories": [],     # list[str]
        "dept_hint":                 "",     # str：局處提示文字
        # ── Phase 1B 預留：公文摘要 ───────────────────────────────────
        "public_summary_text":       "",     # str：三層公文摘要組裝結果
        "preset_reference":          {},     # dict：步驟一預載清單補充參考資訊
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


def prepare_step3_budget_state():
    """同步 Step2 工項勾選結果到 Step3 預算拆解資料。"""
    selected_categories = st.session_state.selected_categories
    selected_sub_categories = st.session_state.selected_sub_categories
    selected_items = list(st.session_state.selected_items)
    valid_item_labels = get_available_item_labels(selected_categories, selected_sub_categories)

    selected_items, valid_item_budgets, removed_labels = prune_invalid_selections(
        selected_items,
        st.session_state.item_budgets,
        valid_item_labels,
    )
    st.session_state.selected_items = selected_items

    if removed_labels:
        st.session_state.selection_warning = "已移除不再適用的工項：" + "、".join(removed_labels)

    existing = {ib["label"]: ib for ib in valid_item_budgets}
    st.session_state.item_budgets = [
        existing.get(label, {"label": label, "ratio": None, "amount": 0})
        for label in selected_items
    ]


def validate_forward_transition(start_step: int, target_step: int):
    """快速跳頁前檢核：沿用序列導引的關卡邏輯。"""
    if target_step <= start_step:
        return True, ""

    for step_idx in range(start_step, target_step):
        if step_idx == 0:
            case_name = (st.session_state.case_name or "").strip()
            dept = (st.session_state.dept or "").strip()
            budget_val = st.session_state.budget or 0
            manual_override = bool(st.session_state.manual_override)
            exclusion_hits = detect_text_keywords(case_name, KWDICT.get("exclusion_keywords", []))
            negative_ok = (not exclusion_hits) or bool(st.session_state.negative_filter_override)
            if not (
                case_name
                and dept not in ("（請選擇）", "")
                and budget_val > 0
                and (budget_val >= PARAMS["min_threshold"] or manual_override)
                and negative_ok
            ):
                return False, "請先完成步驟一必要欄位與進入下一步條件。"

        elif step_idx == 1:
            has_sub_for_each_cat = all(
                any(
                    sid == f"{cid}_NONE" or (
                        (result := get_sub_by_id_global(sid)) and result[0] and result[0]["id"] == cid
                    )
                    for sid in st.session_state.selected_sub_categories
                )
                for cid in st.session_state.selected_categories
            )
            can_next = bool(st.session_state.selected_categories) and has_sub_for_each_cat
            if not can_next:
                return False, "請先完成步驟二：每個類別至少選一個細項或不確定項目。"

        elif step_idx == 2:
            prepare_step3_budget_state()

        elif step_idx == 3:
            total_budget = st.session_state.budget or 0
            item_budgets = st.session_state.item_budgets
            total_allocated = sum(ib.get("amount", 0) or 0 for ib in item_budgets)
            over_budget = total_allocated > total_budget
            all_set = (not item_budgets) or all(
                ib.get("amount", 0) > 0
                or ib.get("is_zero_cost", False)
                or ib.get("is_smart_use", False)
                for ib in item_budgets
            )
            if not (all_set and not over_budget):
                return False, "請先完成步驟四預算檢核（不得超支且各工項金額需有效）。"

    return True, ""


def go_to_step(target_step: int, *, unlock: bool = False, enforce_transition: bool = False):
    """導向指定步驟；可選擇同步更新可跳轉上限並檢核跨步驟條件。"""
    max_step = st.session_state.max_unlocked_step
    if unlock:
        max_step = max(max_step, target_step)
    st.session_state.max_unlocked_step = max_step

    if enforce_transition:
        ok, msg = validate_forward_transition(st.session_state.step, target_step)
        if not ok:
            st.warning(msg)
            return False

    if st.session_state.step != target_step:
        st.session_state.step = target_step
        st.session_state.scroll_to_top = True
        st.rerun()
    return True

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🌿 氣候預算自評系統")
    st.markdown("---")
    st.markdown("**系統說明**")
    st.markdown("""
此工具協助彰化縣各局處承辦人，透過直覺式流程判定計畫與氣候預算的關聯性。

**評估流程：**
1. 帶入計畫基本資訊
2. 系統自動偵測關鍵字
3. 複選計畫類別（最多 3 項）
4. 複選細項分類與氣候工項
5. 填寫各工項預算
6. 確認並匯出評估報告
    """)
    st.markdown("---")
    st.markdown("**預算警示門檻**")
    st.markdown("""
- 🟢 300萬–1000萬：氣候預算潛力：基層守護
- 🟡 1000萬–2000萬：氣候預算潛力：效能升級
- 🔴 2000萬–1億：氣候預算潛力：部門轉型
- 🟣 1億以上：氣候預算潛力：城市重塑
    """)
    st.markdown("---")
    st.markdown("📌 問題回報(Line)：https://line.me/ti/g/twX_HfMGBd")
    if st.button("🔄 重新開始", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🌿 彰化縣氣候預算導引式判讀系統</h1>
    <p>Changhua County · Climate Budget Assessment Tool · v1.2</p>
</div>
""", unsafe_allow_html=True)

# Step bar
steps = ["① 計畫資訊", "② 類別選擇", "③ 工項勾選", "④ 預算拆解", "⑤ 確認匯出"]
step_html = '<div class="step-bar">'
for i, s in enumerate(steps):
    cls = "active" if i == st.session_state.step else ("done" if i < st.session_state.step else "step-item")
    if i < st.session_state.step:
        cls = "step-item done"
    elif i == st.session_state.step:
        cls = "step-item active"
    else:
        cls = "step-item"
    step_html += f'<div class="{cls}">{s}</div>'
step_html += "</div>"
st.markdown(step_html, unsafe_allow_html=True)

# 快速跳頁（僅可跳至已完成/已解鎖步驟）
st.caption("🔁 快速跳頁：可在已填寫過的步驟間直接切換，未解鎖步驟不可提前前往。")
step_nav_cols = st.columns(len(steps))
for i, col in enumerate(step_nav_cols):
    is_unlocked = i <= st.session_state.max_unlocked_step
    is_current = i == st.session_state.step
    btn_label = f"{steps[i]} {'（目前）' if is_current else ''}"
    with col:
        if st.button(
            btn_label,
            key=f"jump_step_{i}",
            disabled=(not is_unlocked) or is_current,
            use_container_width=True,
        ):
            go_to_step(i, enforce_transition=True)

if st.session_state.get("scroll_to_top", False):
    components.html(
        """
        <script>
        window.parent.scrollTo({top: 0, behavior: "instant"});
        </script>
        """,
        height=0,
        width=0,
    )
    st.session_state.scroll_to_top = False

# Breadcrumb
bc_parts = ["彰化縣氣候預算系統"]
if st.session_state.case_name:
    bc_parts.append(st.session_state.case_name[:20] + ("…" if len(st.session_state.case_name) > 20 else ""))
selected_cats = get_taxonomies_by_ids(st.session_state.selected_categories)
if selected_cats:
    cat_summary = "、".join(cat["label"] for cat in selected_cats[:2])
    if len(selected_cats) > 2:
        cat_summary += "…"
    bc_parts.append(cat_summary[:18])
selected_sub_labels = []
for sub_id in st.session_state.selected_sub_categories[:2]:
    _, sub = get_sub_by_id_global(sub_id)
    if sub:
        selected_sub_labels.append(sub["label"])
if selected_sub_labels:
    sub_summary = "、".join(selected_sub_labels)
    if len(st.session_state.selected_sub_categories) > 2:
        sub_summary += "…"
    bc_parts.append(sub_summary[:18])
st.markdown(f'<div class="breadcrumb">📍 {"  ›  ".join(bc_parts)}</div>', unsafe_allow_html=True)

st.markdown("📌 操作說明、各單位填寫情形、客服聯絡資訊：https://reurl.cc/ppWKm8      📌 說明影片：https://youtu.be/nABPUrgEgwo")

# ═══════════════════════════════════════════════════════════════════
# STEP 0 — 計畫基本資訊
# ═══════════════════════════════════════════════════════════════════
if st.session_state.step == 0:
    st.markdown('<div class="section-title">步驟一：帶入計畫基本資訊(依<a href="https://docs.google.com/spreadsheets/d/1jnAL5LCetC_wBvbAzBqVRD3RPV-KU94xn7MJFX8rVow/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer" style="color: #1a237e; text-decoration: underline;">預載清單</a>)</div>', unsafe_allow_html=True)

    case_df, case_error = load_registered_cases()
    use_manual_case_input = st.checkbox(
        "自行輸入計畫資訊、或非採購案類型的業務資訊",
        value=st.session_state.use_manual_case_input,
        help="如非屬預載計畫，勾選後可改為手動填寫標案名稱、主辦局處與決標金額；亦可填寫獎補助業務等非採購案資訊(例如補助購買自行車、電動機車/補助減緩或調適措施)。"
    )

    if st.session_state.use_manual_case_input != use_manual_case_input:
        st.session_state.use_manual_case_input = use_manual_case_input

    case_df = pd.DataFrame()
    case_error = ""
    if not use_manual_case_input:
        case_df, case_error = load_registered_cases()

    col1, col2 = st.columns([3, 2])

    with col1:
        auto_selected = None
        agency = "（請選擇）"
        unit = "（請選擇）"
        case_name = st.session_state.case_name
        dept_other = st.session_state.dept_other

        if not use_manual_case_input:
            if case_error:
                st.warning(f"⚠️ {case_error}，請改用下方手動輸入。")
                use_manual_case_input = True
                st.session_state.use_manual_case_input = True
            else:
                agency_options = ["（請選擇）"] + list(dict.fromkeys(case_df["機關名稱"].tolist()))  # 維持試算表原始順序
                default_agency = st.session_state.agency_name if st.session_state.agency_name in agency_options else "（請選擇）"
                agency = st.selectbox(
                    "🏛️ 機關名稱",
                    options=agency_options,
                    index=agency_options.index(default_agency),
                )

                unit_pool = case_df[case_df["機關名稱"] == agency] if agency != "（請選擇）" else pd.DataFrame()
                unit_options = ["（請選擇）"] + list(dict.fromkeys(unit_pool["單位名稱"].tolist())) if not unit_pool.empty else ["（請選擇）"]  # 維持試算表原始順序
                default_unit = st.session_state.unit_name if st.session_state.unit_name in unit_options else "（請選擇）"
                unit = st.selectbox(
                    "🏢 單位名稱",
                    options=unit_options,
                    index=unit_options.index(default_unit),
                    disabled=agency == "（請選擇）",
                )

                case_pool = unit_pool[unit_pool["單位名稱"] == unit] if unit != "（請選擇）" else pd.DataFrame()
                case_options = ["（請選擇）"] + list(dict.fromkeys(case_pool["標案名稱"].tolist())) if not case_pool.empty else ["（請選擇）"]  # 維持試算表原始順序
                selected_case = case_name if case_name in case_options else "（請選擇）"
                selected_case = st.selectbox(
                    "📌 標案或業務名稱",
                    options=case_options,
                    index=case_options.index(selected_case),
                    disabled=unit == "（請選擇）",
                )

                if selected_case != "（請選擇）":
                    selected_rows = case_pool[case_pool["標案名稱"] == selected_case]
                    if not selected_rows.empty:
                        auto_selected = selected_rows.iloc[0]
                        case_name = str(auto_selected["標案名稱"]).strip()
                        st.session_state.case_name = case_name
                        st.session_state.agency_name = str(auto_selected["機關名稱"]).strip()
                        st.session_state.unit_name = str(auto_selected["單位名稱"]).strip()
                        st.session_state.dept = st.session_state.unit_name
                        st.session_state.preset_reference = extract_preset_reference(auto_selected)
                else:
                    case_name = ""
                    st.session_state.case_name = ""
                    st.session_state.budget = 0
                    st.session_state.dept = ""
                    st.session_state.preset_reference = {}

        if use_manual_case_input:
            st.session_state.preset_reference = {}
            case_name = st.text_input(
                "📌 標案或業務名稱",
                value=st.session_state.case_name,
                placeholder="例：彰化縣○○公園綠美化工程",
                help="請輸入公文中的完整標案名稱，系統將自動偵測氣候關鍵字"
            )

            departments = get_department_options()
            dept_options = ["（請選擇）"] + departments + ["其他"]
            dept_index = 0
            if st.session_state.dept in departments:
                dept_index = dept_options.index(st.session_state.dept)
            elif st.session_state.dept and st.session_state.dept not in ("（請選擇）", ""):
                dept_index = dept_options.index("其他")

            dept = st.selectbox(
                "🏛️ 主辦局處",
                options=dept_options,
                index=dept_index
            )

            dept_other = ""
            if dept == "其他":
                dept_other = st.text_input(
                    "請填寫主辦局處名稱",
                    value=st.session_state.dept_other,
                    placeholder="例：文化局"
                ).strip()

            budget_input = st.text_input(
                "💰 決標金額或預計金額（元）",
                value=str(int(st.session_state.budget)) if st.session_state.budget else "",
                placeholder="例：15000000",
                help="請輸入決標金額或預計金額（純數字，不含逗號）"
            )
        else:
            selected_dept = unit if unit != "（請選擇）" else "（請選擇）"
            if auto_selected is not None:
                st.session_state.budget = parse_budget_from_sheet(auto_selected.get("決標金額", ""))
            st.text_input("📌 標案名稱", value=case_name, disabled=True)
            st.text_input("🏛️ 主辦局處", value=selected_dept if selected_dept != "（請選擇）" else "", disabled=True)
            budget_input = st.text_input(
                "💰 決標金額（元）",
                value=str(int(st.session_state.budget)) if st.session_state.budget else "",
                disabled=True,
                help="此欄位由雲端試算表自動帶入"
            )
            dept = selected_dept
            preset_reference = st.session_state.get("preset_reference", {})
            preset_preview = [
                f"• **{meta['label']}**：{preset_reference.get(key, '')}"
                for key, meta in PRESET_REFERENCE_COLUMNS.items()
                if preset_reference.get(key, "")
            ]
            if preset_preview:
                st.markdown("**🧩 預載清單補充參考（送出時將同步保存）**")
                st.markdown("\n".join(preset_preview))

    with col2:
        # Keyword detection live preview
        kw_matches = detect_keywords(case_name)
        if case_name and kw_matches:
            strong_matches, concept_matches, logic_matches = split_keyword_matches(kw_matches)
            st.markdown("**🔍 偵測到的氣候關鍵字**")
            kw_html = '<div class="kw-suggestion">'
            kw_html += "<b>💡 系統自動辨識到以下關鍵字，建議對應工項：</b><br>"
            for kw in strong_matches[:6]:
                note_text = f'（{kw.get("note", "")}）' if kw.get("note") else ""
                kw_html += f'<span class="kw-tag">#{kw["keyword"]}</span> → {kw["suggested_item"]}{note_text} <code style="background:#eee;padding:1px 4px;border-radius:3px;font-size:0.7rem;">{kw["code"]}</code><br>'
            if concept_matches:
                concept_names = "、".join(kw["keyword"] for kw in concept_matches[:6])
                kw_html += (
                    f'<div style="margin-top:0.35rem;color:#6b5e00;">'
                    f'🧭 概念提示詞：{concept_names}。系統已辨識為「氣候相關」，'
                    f'但尚未自動綁定工項，請下一步確認減緩/調適方向。'
                    f'</div>'
                )
            if logic_matches:
                logic_names = "、".join(kw["keyword"] for kw in logic_matches[:3])
                kw_html += f'<div style="margin-top:0.25rem;color:#1a4731;">🧩 組合條件命中：{logic_names}</div>'
            kw_html += "</div>"
            st.markdown(kw_html, unsafe_allow_html=True)
        elif case_name:
            st.info("📋 未偵測到特定氣候關鍵字，請繼續手動選擇工項類別。")

        optimized = CONFIG.get("optimized_parameters", {})
        high_risk_hits = detect_text_keywords(case_name, optimized.get("high_risk_keywords", []))
        adaptation_hits = detect_text_keywords(case_name, optimized.get("adaptation_keywords", []))

        if high_risk_hits:
            st.markdown(
                f'<div class="alert-red">⚠️ 偵測到高隱含碳關鍵字：{"、".join(high_risk_hits)}。'
                '建議於後續步驟完整檢核低碳建材、能效與工程碳排。</div>',
                unsafe_allow_html=True
            )
        if adaptation_hits:
            st.markdown(
                f'<div class="alert-green">💧 偵測到氣候調適關鍵字：{"、".join(adaptation_hits)}。'
                '系統將優先引導至水利/防洪/韌性相關工項。</div>',
                unsafe_allow_html=True
            )

        # Budget display
        try:
            budget_val = int(budget_input.replace(",", "").replace(" ", "")) if budget_input else 0
        except:
            budget_val = 0

        if budget_val > 0:
            alert = get_alert_level(budget_val)
            st.markdown(f"""
            <div class="budget-display">
                <div class="label">決標金額</div>
                <div class="amount">{fmt_twd(budget_val)}</div>
                <div style="margin-top:0.5rem; font-size:0.85rem; opacity:0.9">{alert['badge']} {alert['label']}</div>
            </div>
            """, unsafe_allow_html=True)

    # Budget validation alerts
    if budget_val > 0:
        if budget_val >= PARAMS["extreme_alert_threshold"]:
            st.markdown(f'<div class="alert-purple">⛔ {UI["extreme_alert_warning"]}</div>', unsafe_allow_html=True)
        elif budget_val >= PARAMS["high_alert_threshold"]:
            st.markdown(f'<div class="alert-red">{UI["high_alert_warning"]}</div>', unsafe_allow_html=True)
        elif budget_val >= PARAMS["medium_alert_threshold"]:
            st.markdown(f'<div class="alert-yellow">{UI["medium_alert_warning"]}</div>', unsafe_allow_html=True)
        elif budget_val >= PARAMS["min_threshold"]:
            st.markdown(f'<div class="alert-green">{UI["threshold_pass_warning"]}</div>', unsafe_allow_html=True)

    # Below threshold
    below_threshold = budget_val > 0 and budget_val < PARAMS["min_threshold"]
    if below_threshold:
        st.markdown(f'<div class="alert-yellow">⚠️ {UI["exclusion_warning"]}</div>', unsafe_allow_html=True)
        optimized = CONFIG.get("optimized_parameters", {})
        low_budget_hits = detect_text_keywords(case_name, optimized.get("adaptation_keywords", []))
        if low_budget_hits:
            hint_text = UI.get("manual_override_hint_text", optimized.get("manual_override_hints", ""))
            st.markdown(f'<div class="alert-green">📝 {hint_text}</div>', unsafe_allow_html=True)
        manual_override = st.checkbox(UI["manual_override_label"], value=st.session_state.manual_override)
    else:
        manual_override = False

    # Exclusion guidelines
    st.caption(EXPANDER_HINT_TEXT)
    with st.expander("📋 以下樣態計畫建議不需納入評估（點擊展開）"):
        for guideline in UI["exclusion_guidelines"]:
            st.markdown(f"• {guideline}")

    # Proceed button
    selected_dept = dept_other if dept == "其他" else dept

    forced_review_threshold = CONFIG.get("weighting_parameters", {}).get(
        "high_budget_forced_review_threshold", 50000000
    )
    high_budget_forced_review = (
        budget_val >= forced_review_threshold and case_name and not kw_matches
    )
    exclusion_hits = detect_text_keywords(case_name, KWDICT.get("exclusion_keywords", []))

    if high_budget_forced_review:
        st.markdown(
            f'<div class="alert-purple">🧭 本案金額超過{forced_review_threshold:,}元且未命中關鍵字，依防漂綠規則仍需強制進入下一步檢核。</div>',
            unsafe_allow_html=True
        )

    if exclusion_hits:
        st.markdown(
            f'<div class="alert-red">⛔ 偵測到排除關鍵字：{"、".join(exclusion_hits)}。本案可能屬一般行政庶務，除非具備特定氣候政策目標，否則建議不納入評估。</div>',
            unsafe_allow_html=True
        )
        st.session_state.negative_filter_override = st.checkbox(
            "本案具備明確氣候政策目標，仍要進入下一步檢核",
            value=st.session_state.negative_filter_override
        )
    else:
        st.session_state.negative_filter_override = False

    can_proceed = (
        case_name.strip()
        and selected_dept not in ("（請選擇）", "")
        and budget_val > 0
        and (budget_val >= PARAMS["min_threshold"] or manual_override)
        and (not exclusion_hits or st.session_state.negative_filter_override)
    )

    if st.button("下一步：選擇計畫及工項類別 →", disabled=not can_proceed, type="primary", use_container_width=True):
        st.session_state.case_name = case_name
        st.session_state.dept = selected_dept
        st.session_state.dept_other = dept_other
        st.session_state.budget = budget_val
        st.session_state.manual_override = manual_override
        st.session_state.kw_matches = kw_matches
        st.session_state.negative_filter_override = st.session_state.negative_filter_override
        go_to_step(1, unlock=True)

    if not can_proceed and (case_name or budget_val):
        missing = []
        if not case_name.strip(): missing.append("標案名稱")
        if selected_dept in ("（請選擇）", ""):
            missing.append("主辦局處")
        if not budget_val: missing.append("決標金額")
        if below_threshold and not manual_override: missing.append("確認繼續評估")
        if exclusion_hits and not st.session_state.negative_filter_override: missing.append("負向排除覆核")
        if missing:
            st.caption(f"⚠️ 尚需填寫：{'、'.join(missing)}")

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — 工程類別選擇
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 1:
    st.markdown('<div class="section-title">步驟二：複選計畫類別（最多 3 項）</div>', unsafe_allow_html=True)
    st.caption("可先選最接近者，再補選其他相關類別；補選類別或細項時，不會直接清空既有工項。")

    # 顯示前一步產生的警告（例如超過 3 項的提示）
    if st.session_state.selection_warning:
        st.warning(st.session_state.selection_warning)
        st.session_state.selection_warning = ""

    # ── 判讀理由面板（Phase 1 新增）──────────────────────────────
    explain_html = build_explain_html(
        st.session_state.kw_matches,
        st.session_state.manual_override,
        st.session_state.budget,
    )
    if explain_html:
        st.markdown(explain_html, unsafe_allow_html=True)

    # Show keyword suggestions
    if st.session_state.kw_matches:
        strong_matches, _, logic_matches = split_keyword_matches(st.session_state.kw_matches)
        suggestion_pool = strong_matches + logic_matches
        suggested_cats = list({kw["category_id"] for kw in suggestion_pool if kw.get("category_id")})
        kw_names = [kw["keyword"] for kw in st.session_state.kw_matches]
        st.markdown(f'<div class="kw-suggestion">💡 根據標案名稱中的關鍵字（{"、".join(kw_names[:5])}），系統建議優先檢視以下高亮類別 ↓</div>', unsafe_allow_html=True)
    else:
        suggested_cats = []

    # Category cards — 2 columns
    taxonomy = LOGIC["taxonomy"]
    col1, col2 = st.columns(2)

    for i, cat in enumerate(taxonomy):
        is_suggested = cat["id"] in suggested_cats
        is_selected = cat["id"] in st.session_state.selected_categories

        with (col1 if i % 2 == 0 else col2):
            badge = "⭐ 建議類別 · " if is_suggested else ""
            selected_mark = "✅ " if is_selected else ""
            button_key = f"cat_{cat['id']}"
            inject_button_style(button_key, is_selected=is_selected, is_suggested=is_suggested)

            if st.button(
                f"{selected_mark}{cat['icon']} {cat['label']}\n{badge}（{cat['description'][:20]}…）",
                key=button_key,
                use_container_width=True,
                type="secondary"
            ):
                updated_categories = list(st.session_state.selected_categories)
                if cat["id"] in updated_categories:
                    # 取消選取：同時清除不再有效的細項
                    updated_categories.remove(cat["id"])
                    valid_sub_ids = {entry["sub"]["id"] for entry in get_available_sub_entries(updated_categories)}
                    st.session_state.selected_sub_categories = [
                        sub_id for sub_id in st.session_state.selected_sub_categories
                        if sub_id in valid_sub_ids
                    ]
                    st.session_state.selected_categories = updated_categories
                    if "A" not in updated_categories:
                        st.session_state.engineering_guideline_type = ""
                elif len(updated_categories) >= 3:
                    st.session_state.selection_warning = "⚠️ 計畫類別最多可選 3 項，請先取消其中一項再補選。"
                else:
                    updated_categories.append(cat["id"])
                    st.session_state.selected_categories = updated_categories
                st.rerun()

    # Sub-category selection
    if st.session_state.selected_categories:
        st.markdown("---")
        selected_categories = get_taxonomies_by_ids(st.session_state.selected_categories)
        st.markdown('<div class="section-title">選擇細項分類（依已選類別聯合顯示，可複選）</div>', unsafe_allow_html=True)
        st.caption("如果沒有合適的細項，可嘗試選取其他的計畫類別。")

        suggested_subs = list({
            kw["sub_id"] for kw in st.session_state.kw_matches
            if kw.get("category_id") in st.session_state.selected_categories
        })

        available_sub_entries = get_available_sub_entries(st.session_state.selected_categories)

        # ── 依計畫類別分組渲染細項 + 各類末尾「不確定適合項目」逃生出口 ──
        # 先將 available_sub_entries 按類別分組
        cat_sub_groups: dict = {}
        for entry in available_sub_entries:
            cid = entry["category"]["id"]
            cat_sub_groups.setdefault(cid, {"category": entry["category"], "subs": []})
            cat_sub_groups[cid]["subs"].append(entry["sub"])

        for cid, group in cat_sub_groups.items():
            grp_cat = group["category"]
            grp_subs = group["subs"]
            none_id = f"{cid}_NONE"

            # 該類別目前已選的細項（不含 _NONE）
            cat_real_selected = [
                sid for sid in st.session_state.selected_sub_categories
                if sid != none_id and any(s["id"] == sid for s in grp_subs)
            ]
            none_selected = none_id in st.session_state.selected_sub_categories

            # 類別群組標題
            st.markdown(
                f'<div style="background:#e8f0e8;border-left:4px solid #2d6a4f;'
                f'padding:0.4rem 0.8rem;border-radius:0 6px 6px 0;margin:0.8rem 0 0.4rem 0;'
                f'font-weight:700;font-size:0.9rem;color:#1a4731;">'
                f'{grp_cat["icon"]} {grp_cat["label"]}</div>',
                unsafe_allow_html=True,
            )

            # 正常細項（兩欄並排）
            subcol1, subcol2 = st.columns(2)
            all_items = grp_subs  # 正常細項清單
            for j, sub in enumerate(all_items):
                is_sub_suggested = sub["id"] in suggested_subs
                is_sub_selected  = sub["id"] in st.session_state.selected_sub_categories
                # 若本類別已選「_NONE」，其他細項強制顯示為不可選（disabled 透過樣式模擬）
                force_disabled = none_selected

                with (subcol1 if j % 2 == 0 else subcol2):
                    badge        = "⭐ " if is_sub_suggested else ""
                    selected_mark = "✅ " if is_sub_selected else ""
                    button_key   = f"sub_{sub['id']}"
                    inject_button_style(
                        button_key,
                        is_selected=is_sub_selected and not force_disabled,
                        is_suggested=is_sub_suggested and not is_sub_selected and not force_disabled,
                    )
                    if st.button(
                        f"{selected_mark}{badge}{grp_cat['icon']} {sub['label']}\n📌 {sub['examples'][:28]}",
                        key=button_key,
                        use_container_width=True,
                        type="secondary",
                        disabled=force_disabled,
                    ):
                        updated_sub = list(st.session_state.selected_sub_categories)
                        if sub["id"] in updated_sub:
                            updated_sub.remove(sub["id"])
                        else:
                            updated_sub.append(sub["id"])
                        st.session_state.selected_sub_categories = updated_sub
                        st.rerun()

            # ── 逃生出口按鈕（各類別末尾，整列單獨一行）──
            none_key = f"sub_{none_id}"
            none_is_selected = none_selected
            # 若本類別已有其他細項被勾選，_NONE 不可點
            none_disabled = len(cat_real_selected) > 0
            inject_button_style(none_key, is_selected=none_is_selected)
            if st.button(
                f"{'✅ ' if none_is_selected else ''}⬜ 不確定適合項目，在下一頁展開氣候工項檢查",
                key=none_key,
                use_container_width=True,
                type="secondary",
                disabled=none_disabled,
                help="已點選其他細項時此按鈕不可用；若本類別確實沒有合適細項，點選此項即可繼續。",
            ):
                updated_sub = list(st.session_state.selected_sub_categories)
                if none_id in updated_sub:
                    updated_sub.remove(none_id)
                else:
                    # 清除本類別其他細項（理論上此時 cat_real_selected 已為空，雙重保險）
                    for sid in cat_real_selected:
                        if sid in updated_sub:
                            updated_sub.remove(sid)
                    updated_sub.append(none_id)
                st.session_state.selected_sub_categories = updated_sub
                st.rerun()

        selected_cat_labels = "、".join(cat["label"] for cat in selected_categories)
        st.info(f"已選計畫類別（{len(selected_categories)}/3）：{selected_cat_labels}")
        if st.session_state.selected_sub_categories:
            # 顯示時過濾掉 _NONE 虛擬項目，只顯示真實細項名稱
            real_sub_ids = [
                sid for sid in st.session_state.selected_sub_categories
                if not sid.endswith("_NONE")
            ]
            none_cat_labels = [
                get_taxonomy_by_id(sid.replace("_NONE", ""))["label"]
                for sid in st.session_state.selected_sub_categories
                if sid.endswith("_NONE") and get_taxonomy_by_id(sid.replace("_NONE", ""))
            ]
            parts = []
            if real_sub_ids:
                real_text = "、".join(
                    sub["label"]
                    for sub_id in real_sub_ids
                    if (sub := get_sub_by_id_global(sub_id)[1])
                )
                parts.append(real_text)
            if none_cat_labels:
                parts.append(f"（{' / '.join(none_cat_labels)} 類別展開全部工項）")
            st.info("已選細項分類（" + str(len(real_sub_ids)) + " 項）：" + "　".join(parts))

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← 返回", use_container_width=True):
            go_to_step(0)
    with col_next:
        # 必須至少選一個細項（含逃生出口 _NONE）才能繼續
        has_sub_for_each_cat = all(
            any(
                sid == f"{cid}_NONE" or (
                    (result := get_sub_by_id_global(sid)) and result[0] and result[0]["id"] == cid
                )
                for sid in st.session_state.selected_sub_categories
            )
            for cid in st.session_state.selected_categories
        )
        can_next = bool(st.session_state.selected_categories) and has_sub_for_each_cat
        if not can_next and st.session_state.selected_categories:
            st.caption("⚠️ 每個計畫類別都需至少選擇一個細項，或點選「不確定適合項目」後才能繼續。")
        if st.button("下一步：勾選氣候工項 →", disabled=not can_next, type="primary", use_container_width=True):
            go_to_step(2, unlock=True)

# ═══════════════════════════════════════════════════════════════════
# STEP 2 — 工項勾選
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 2:
    st.markdown('<div class="section-title">步驟三：勾選氣候相關工項（依已選細項聯合顯示）</div>', unsafe_allow_html=True)

    selected_categories = st.session_state.selected_categories
    selected_sub_categories = st.session_state.selected_sub_categories
    item_source_entries = get_item_sources(selected_categories, selected_sub_categories)

    # 判斷是否有任何 _NONE 逃生出口（該類別展開全部工項）
    none_cats = [
        get_taxonomy_by_id(sid.replace("_NONE", ""))
        for sid in selected_sub_categories if sid.endswith("_NONE")
    ]
    none_cats = [c for c in none_cats if c]
    real_sub_ids = [sid for sid in selected_sub_categories if not sid.endswith("_NONE")]

    if real_sub_ids or none_cats:
        lines = []
        for entry in item_source_entries:
            cat = entry["category"]
            sub = entry["sub"]
            # 判斷這條細項是來自真實選取，還是 _NONE 展開
            is_from_none = cat in none_cats and sub["id"] not in real_sub_ids
            marker = "（全部展開）" if is_from_none else ""
            lines.append(f"{cat['icon']} {cat['label']} › {sub['label']}{marker}")
        # 去重保持順序
        seen = set(); deduped = []
        for l in lines:
            if l not in seen:
                seen.add(l); deduped.append(l)
        st.markdown("**已選細項聯集：**")
        for desc in deduped:
            st.markdown(f"- {desc}")
        st.caption("📌 以下顯示已選細項的工項聯集，重複工項會自動去重。")

    # Suggested items from keywords — build lookup: label → triggering keyword(s)
    suggested_items_labels = {kw["suggested_item"] for kw in st.session_state.kw_matches}
    # map item label → list of keywords that triggered it (for explainability tooltip)
    item_trigger_map: dict[str, list[str]] = {}
    for kw in st.session_state.kw_matches:
        lbl = kw.get("suggested_item", "")
        if lbl:
            item_trigger_map.setdefault(lbl, []).append(kw["keyword"])

    st.markdown("**請勾選本案中包含的氣候相關工項（可複選）：**")

    selected_items = list(st.session_state.selected_items)
    valid_item_labels = get_available_item_labels(selected_categories, selected_sub_categories)
    invalid_selected_items = [
        label for label in selected_items
        if label not in valid_item_labels
    ]
    if invalid_selected_items:
        st.warning(
            "⚠️ 下列氣候工項：**" + "、".join(invalid_selected_items) + "**"
            "　與您的計畫名稱有關，但上一步您並未點選對應的類別／細項。"
            "如需補充，可至頁面下方按「返回」補充點選。"
        )

    rendered = set()
    for entry in item_source_entries:
        cat = entry["category"]
        sub = entry["sub"]
        # ── 群組標題（橫跨全寬）
        st.markdown(
            f'<div style="background:#e8f0e8;border-left:4px solid #2d6a4f;'
            f'padding:0.45rem 0.8rem;border-radius:0 6px 6px 0;margin:0.8rem 0 0.4rem 0;'
            f'font-weight:700;font-size:0.92rem;color:#1a4731;">'
            f'{cat["icon"]} {cat["label"]}｜{sub["label"]}</div>',
            unsafe_allow_html=True,
        )

        # 收集此 sub 下尚未渲染的工項
        sub_items_to_render = []
        for item in sub["items"]:
            if item["label"] in rendered:
                continue
            rendered.add(item["label"])
            sub_items_to_render.append(item)

        if not sub_items_to_render:
            st.caption("（本細項工項已於其他群組顯示）")
            continue

        # ── 兩欄並排，點卡片切換選取
        col_left, col_right = st.columns(2)
        for idx, item in enumerate(sub_items_to_render):
            is_suggested = item["label"] in suggested_items_labels or any(
                kw["suggested_item"] == item["label"] for kw in st.session_state.kw_matches
            )
            is_checked = item["label"] in selected_items
            col = col_left if idx % 2 == 0 else col_right
            item_key = f"item_{safe_key(item['label'])}"

            with col:
                star = "⭐ " if is_suggested else ""
                codes_str = "  ".join(
                    item.get("mitigation_codes", []) + item.get("adaptation_codes", [])
                )
                alert_txt = f"\n⚠️ {item['alert']}" if item.get("alert") else ""
                check_mark = "✅ " if is_checked else ""

                # 按鈕樣式注入
                inject_button_style(item_key, is_selected=is_checked, is_suggested=is_suggested and not is_checked)

                btn_label = (
                    f"{check_mark}{star}{item['label']}\n"
                    f"{codes_str}{alert_txt}\n"
                    f"📋 {item['policy'][:36]}{'…' if len(item['policy']) > 36 else ''}"
                )
                if st.button(btn_label, key=item_key, use_container_width=True, type="secondary"):
                    if item["label"] in selected_items:
                        selected_items.remove(item["label"])
                    else:
                        selected_items.append(item["label"])
                    st.session_state.selected_items = selected_items
                    st.rerun()

                # ── Phase 1：顯示觸發來源（關鍵字說明）─────────────
                if is_suggested and item["label"] in item_trigger_map:
                    triggers = item_trigger_map[item["label"]]
                    kw_tags = "".join(
                        f'<span style="display:inline-block;background:#f39c12;color:white;'
                        f'padding:0.1rem 0.45rem;border-radius:10px;font-size:0.7rem;'
                        f'font-weight:600;margin:0.1rem 0.15rem 0 0;">#{t}</span>'
                        for t in triggers
                    )
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#8f5c00;margin:-0.3rem 0 0.3rem 0.2rem;">'
                        f'🔑 由關鍵字觸發：{kw_tags}</div>',
                        unsafe_allow_html=True,
                    )

    st.session_state.selected_items = selected_items

    # 顯示目前已勾選工項數摘要
    valid_count = len([l for l in selected_items if l in valid_item_labels])
    total_count = len(selected_items)
    if total_count > 0:
        extra = total_count - valid_count
        count_msg = f"✅ 已勾選 **{valid_count}** 個氣候工項"
        if extra > 0:
            count_msg += f"，另有 **{extra}** 個超出範圍（進入下一步時自動移除）"
        st.info(count_msg)
    else:
        st.caption("本步驟可先略過，下一步可直接進行預算檢視與補充。")

    # ── 專業工程減碳檢核提示（依已選計畫類別，展開式顯示）────────
    checklists = LOGIC.get("engineering_checklists", {})
    checklist_cats = [
        cat for cat in get_taxonomies_by_ids(selected_categories)
        if cat["id"] in checklists
    ]
    if checklist_cats:
        st.markdown("---")
        st.markdown(
            '<div class="section-title">🔍 工程減碳指引自主檢核</div>',
            unsafe_allow_html=True,
        )
        st.caption(EXPANDER_HINT_TEXT)
        for cat in checklist_cats:
            items_html = "".join(
                f'<li style="margin:0.3rem 0;font-size:0.86rem;">{it}</li>'
                for it in checklists[cat["id"]]
            )
            st.markdown(
                f'<details style="background:#f8fdf8;border:1px solid #c8e6c9;border-radius:8px;'
                f'padding:0.6rem 1rem;margin:0.4rem 0;">'
                f'<summary style="font-weight:700;color:#1a4731;cursor:pointer;">'
                f'{cat["icon"]} {cat["label"]} — 減碳指引檢核清單</summary>'
                f'<ul style="margin:0.5rem 0 0 1rem;padding:0;">{items_html}</ul>'
                f'</details>',
                unsafe_allow_html=True,
            )

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← 返回", use_container_width=True):
            go_to_step(1)
    with col_next:
        if st.button("下一步：填寫工項預算 →", type="primary", use_container_width=True):
            prepare_step3_budget_state()
            go_to_step(3, unlock=True)

# ═══════════════════════════════════════════════════════════════════
# STEP 3 — 預算拆解
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 3:
    st.markdown('<div class="section-title">步驟四：填寫各工項氣候預算</div>', unsafe_allow_html=True)

    if st.session_state.selection_warning:
        st.info(st.session_state.selection_warning)
        st.session_state.selection_warning = ""

    total_budget = st.session_state.budget
    item_budgets = st.session_state.item_budgets

    # Running total
    total_allocated = sum(ib.get("amount", 0) or 0 for ib in item_budgets)
    remaining = total_budget - total_allocated
    over_budget = total_allocated > total_budget

    # Sticky budget monitor
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="budget-display">
            <div class="label">標案總預算</div>
            <div class="amount" style="font-size:1.4rem">{fmt_twd(total_budget)}</div>
            <div style="font-size:0.78rem;opacity:0.75;margin-top:0.25rem">≈ {total_budget/10000:.1f} 萬元</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="budget-display" style="background:linear-gradient(135deg,#1a6090,#2980b9)">
            <div class="label">已分配氣候預算</div>
            <div class="amount" style="font-size:1.4rem">{fmt_twd(total_allocated)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        cls = "budget-over" if over_budget else "budget-remaining"
        st.markdown(f"""
        <div class="{cls}">
            <div class="label">{"⚠️ 超出預算！" if over_budget else "✅ 剩餘可用預算"}</div>
            <div class="amount" style="font-size:1.4rem">{fmt_twd(abs(remaining))}</div>
        </div>
        """, unsafe_allow_html=True)

    if over_budget:
        st.error("🚫 各工項金額加總已超出標案總預算，請調整後再繼續。")

    st.markdown("---")
    st.markdown("**請為每個氣候工項填寫參考金額（元）：**")
    if not item_budgets:
        st.info("目前尚未勾選工項，可直接前往下一步完成填報。")

    updated_items = []
    for idx, ib in enumerate(item_budgets):
        label = ib["label"]
        st.markdown(f"**{idx+1}. {label}**")

        if is_pure_zero_cost(label):
            # 純零成本：施工決策/現場再利用，不顯示金額欄，引導填效益
            st.markdown(
                '<div style="background:#fffbf0;border-left:4px solid #f39c12;'
                'border-radius:0 8px 8px 0;padding:0.6rem 1rem;margin:0.3rem 0;'
                'font-size:0.88rem;color:#7d5a00;">'
                '💡 本工項屬於「不花錢／少花錢」的工法或設計選擇，不需填寫獨立預算金額。'
                '請填寫下方「<b>工程量體縮減及其他效益（選填）</b>」欄位，記錄本工項的實質減碳效益。'
                '</div>',
                unsafe_allow_html=True,
            )
            amount = 0
            pct_of_total = 0.0
        else:
            col_amt, col_calc = st.columns([3, 2])
            with col_amt:
                saved_amount_wan = round((ib.get("amount", 0) or 0) / 10000, 1)
                max_wan = round(total_budget / 10000, 1)
                # 若尚未填過（0），value 傳 None 讓欄位顯示空白，避免預填 0.0 干擾輸入
                default_wan = None if saved_amount_wan == 0.0 else saved_amount_wan
                amount_wan = st.number_input(
                    "工項參考金額（萬元）",
                    min_value=0.0,
                    max_value=max_wan,
                    value=default_wan,
                    step=1.0,
                    format="%.1f",
                    placeholder="請輸入金額（萬元）",
                    key=f"amt_{idx}"
                )
                amount = round((amount_wan or 0) * 10000)   # 內部仍以元儲存
            with col_calc:
                pct_of_total = amount / total_budget * 100 if total_budget else 0
                st.metric("佔總預算", f"{pct_of_total:.1f}%", delta=fmt_twd(amount))
            # 聰明使用型：金額欄下方加提示
            if is_smart_use_item(label):
                st.markdown(
                    '<div style="background:#f0fdf4;border-left:3px solid #52b788;'
                    'border-radius:0 6px 6px 0;padding:0.5rem 0.9rem;margin:0.2rem 0 0.4rem 0;'
                    'font-size:0.82rem;color:#1a4731;">'
                    '💡 本工項如涵蓋「不花錢／少花錢」的工法或設計選擇（如 CLSM 替代混凝土、'
                    '循環建材導入），可於本頁下方「<b>工程量體縮減及其他效益（選填）</b>」欄位，'
                    '記錄本工項的實質效益。'
                    '</div>',
                    unsafe_allow_html=True,
                )

        updated_items.append({
            "label": label,
            "ratio": round(pct_of_total, 1),
            "amount": int(amount),
            "is_zero_cost": is_pure_zero_cost(label),   # 純零成本：金額固定為 0
            "is_smart_use": is_smart_use_item(label),   # 聰明使用型：有採購但涵蓋量體效益
        })

        st.markdown("<hr style='margin:0.5rem 0; border-color:#e8f0e8'>", unsafe_allow_html=True)

    st.session_state.item_budgets = updated_items

    heat_prompt_triggered = should_trigger_heat_safety_prompt(
        st.session_state.case_name,
        st.session_state.selected_categories,
        st.session_state.dept,
    )
    st.session_state.heat_safety_prompt_triggered = heat_prompt_triggered

    if heat_prompt_triggered:
        st.markdown("---")
        st.markdown(
            '<div style="background:#fff8e8;border-left:4px solid #f39c12;'
            'border-radius:0 8px 8px 0;padding:0.8rem 1rem;margin:0.4rem 0 0.8rem 0;">'
            '<b>🌡️ 高溫作業調適提醒</b><br>'
            '<span style="font-size:0.86rem;color:#5f4a00;">'
            '本案可能涉及戶外施工或高溫作業環境，建議檢視施工管理調適措施。'
            '</span><br>'
            '<span style="font-size:0.78rem;color:#7d5a00;">'
            '此提醒用於補充判讀施工過程之氣候風險，不影響氣候預算總額計算。'
            '</span></div>',
            unsafe_allow_html=True,
        )
        heat_response = st.radio(
            "請選擇本案回應狀態：",
            options=["已納入", "部分納入", "尚未納入", "不適用"],
            index=["已納入", "部分納入", "尚未納入", "不適用"].index(
                st.session_state.get("heat_safety_response")
            ) if st.session_state.get("heat_safety_response") in ["已納入", "部分納入", "尚未納入", "不適用"] else 2,
            horizontal=True,
            key="heat_safety_response_radio",
        )
        st.session_state.heat_safety_response = heat_response

        if heat_response in ["已納入", "部分納入"]:
            heat_note = st.text_area(
                "補充說明（選填）",
                value=st.session_state.get("heat_safety_note", ""),
                placeholder="例：已規劃夏季高溫時段調整工序、補水休息點與遮蔭設施。",
                height=80,
                key="heat_safety_note_input",
            )
            st.session_state.heat_safety_note = heat_note.strip()
        else:
            st.session_state.heat_safety_note = ""
    else:
        st.session_state.heat_safety_response = ""
        st.session_state.heat_safety_note = ""

    # ── 量體縮減及其他效益欄位（依已選工項動態顯示，零成本工項一律觸發）──
    reduction_fields = get_physical_reduction_fields(updated_items)
    has_zero_cost = any(ib.get("is_zero_cost", False) for ib in updated_items)
    show_reduction_section = bool(reduction_fields) or has_zero_cost

    if show_reduction_section:
        st.markdown("---")
        st.markdown(
            '<div class="section-title">📐 工程量體縮減及其他效益（選填）</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "以下工項涉及**現地材料再利用、量體縮減或設計端減量**，"
            "這類效益節省下來的成本通常不直接出現在工程費用中，"
            "但仍是重要的減碳貢獻。若能估算數量或說明效益，可填入作為評估依據。"
        )

        current_reductions = dict(st.session_state.get("physical_reductions", {}))
        rcol1, rcol2 = st.columns(2)

        if "soil_reduction_ton" in reduction_fields or has_zero_cost:
            with rcol1:
                soil_val = current_reductions.get("soil_reduction_ton", 0)
                soil_new = st.number_input(
                    "🪨 減少土方購置量（公噸）",
                    min_value=0,
                    value=int(soil_val) if int(soil_val) > 0 else None,
                    placeholder="請輸入公噸數",
                    help="因現地土方挖填平衡、就地取材，減少外購土石方的估算量。",
                    key="soil_reduction_input",
                )
                soil_new = soil_new or 0
                current_reductions["soil_reduction_ton"] = int(soil_new)
                if soil_new > 0:
                    co2_eq = round(soil_new * 0.005, 1)
                    st.caption(f"粗估減碳效益：約 {co2_eq} tCO₂e（以平均運距 20km 估算）")

        if "waste_reduction_ton" in reduction_fields or has_zero_cost:
            with rcol2:
                waste_val = current_reductions.get("waste_reduction_ton", 0)
                waste_new = st.number_input(
                    "♻️ 減少廢棄物外運處理量（公噸）",
                    min_value=0,
                    value=int(waste_val) if int(waste_val) > 0 else None,
                    placeholder="請輸入公噸數",
                    help="因現地再利用（RAP、道碴、污泥資源化等），減少需外運廢棄物的估算量。",
                    key="waste_reduction_input",
                )
                waste_new = waste_new or 0
                current_reductions["waste_reduction_ton"] = int(waste_new)
                if waste_new > 0:
                    co2_eq = round(waste_new * 0.008, 1)
                    st.caption(f"粗估減碳效益：約 {co2_eq} tCO₂e（以一般廢棄物處理排放係數估算）")

        # ── 新欄位：減少水泥等建材使用量 ──
        with rcol1:
            cement_val = current_reductions.get("cement_reduction_ton", 0)
            cement_new = st.number_input(
                "🏗️ 減少水泥等建材使用量（公噸）",
                min_value=0,
                value=int(cement_val) if int(cement_val) > 0 else None,
                placeholder="請輸入公噸數",
                help="因結構輕量化、低碳建材替代、預鑄工法等，減少傳統水泥或高碳建材的使用量。",
                key="cement_reduction_input",
            )
            cement_new = cement_new or 0
            current_reductions["cement_reduction_ton"] = int(cement_new)
            if cement_new > 0:
                co2_eq = round(cement_new * 0.83, 1)  # 粗估：生產1公噸水泥約排放0.83 tCO2e
                st.caption(f"粗估減碳效益：約 {co2_eq} tCO₂e（以水泥生產排放係數估算）")

        # ── 新欄位：其他未呈現於預算的效益說明 ──
        with rcol2:
            other_val = current_reductions.get("other_benefit_note", "")
            other_new = st.text_area(
                "📝 其他未呈現於預算的效益說明",
                value=other_val,
                placeholder="例：採用砌石護岸取代混凝土護岸，具備生態廊道功能；施工期間取用附近污水廠放流水作為工程用水，減少自來水使用……",
                height=100,
                help="填入難以量化但具有減碳、調適或生態效益的說明，供審查參考。",
                key="other_benefit_input",
            )
            current_reductions["other_benefit_note"] = other_new.strip()

        st.session_state.physical_reductions = current_reductions

    # Recalculate for button state
    total_allocated = sum(ib.get("amount", 0) or 0 for ib in updated_items)
    over_budget = total_allocated > total_budget
    # 純零成本工項金額固定為 0；聰明使用型允許填 0；一般工項才強制填 > 0
    all_set = (not updated_items) or all(
        ib.get("amount", 0) > 0
        or ib.get("is_zero_cost", False)
        or ib.get("is_smart_use", False)
        for ib in updated_items
    )

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← 返回", use_container_width=True):
            go_to_step(2)
    with col_next:
        can_next = all_set and not over_budget
        if st.button("下一步：確認並匯出報告 →", disabled=not can_next, type="primary", use_container_width=True):
            go_to_step(4, unlock=True)
        if not can_next:
            if over_budget:
                st.caption("🚫 工項金額加總超出標案總預算，請調整。")
            elif not all_set:
                st.caption("⚠️ 請為所有工項設定預算金額（填入大於 0 的數值）。")

# ═══════════════════════════════════════════════════════════════════
# STEP 4 — 確認與匯出
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 4:
    st.markdown('<div class="section-title">步驟五：確認評估結果並匯出</div>', unsafe_allow_html=True)

    state = st.session_state
    alert = get_alert_level(state.budget)
    selected_cats = get_taxonomies_by_ids(state.selected_categories)
    selected_sub_entries = []
    for sub_id in state.selected_sub_categories:
        cat, sub = get_sub_by_id_global(sub_id)
        if cat and sub:
            selected_sub_entries.append({"category": cat, "sub": sub})

    climate_total = sum(ib.get("amount", 0) for ib in state.item_budgets)
    climate_ratio = climate_total / state.budget * 100 if state.budget else 0

    # Summary display
    col_info, col_chart = st.columns([3, 2])

    with col_info:
        st.markdown('<div class="summary-card">', unsafe_allow_html=True)
        st.markdown(f"""
**📌 標案名稱：** {state.case_name}

**🏛️ 主辦局處：** {state.dept}

**💰 計畫總經費：** {fmt_twd(state.budget)}

**{alert['badge']} 計畫規模（隱含碳潛力）：** {alert['label']}
        """)
        st.markdown(
            f'<div style="font-size:0.82rem;color:#666;margin-top:-0.5rem;margin-bottom:0.5rem;">'
            f'{alert["desc"]}</div>',
            unsafe_allow_html=True,
        )

        if selected_cats:
            st.markdown("**🗂️ 計畫類別（複選）：**")
            for cat in selected_cats:
                st.markdown(f"- {cat['icon']} {cat['label']}")

        if selected_sub_entries:
            st.markdown("**📂 細項分類（複選）：**")
            for entry in selected_sub_entries:
                st.markdown(f"- {entry['category']['icon']} {entry['sub']['label']}")
        elif selected_cats:
            st.markdown("**📂 細項分類：** 未限定（採所有已選類別之工項聯集）")

        st.markdown("**✅ 氣候相關工項：**")
        for ib in state.item_budgets:
            pct = ib['amount'] / state.budget * 100 if state.budget else 0
            st.markdown(f"- {ib['label']}：{fmt_twd(ib['amount'])} （{pct:.1f}%）")

        # 量體縮減摘要
        phys = state.get("physical_reductions", {})
        phys_lines = []
        if phys.get("soil_reduction_ton", 0):
            phys_lines.append(f"🪨 減少土方購置 **{phys['soil_reduction_ton']}** 公噸")
        if phys.get("waste_reduction_ton", 0):
            phys_lines.append(f"♻️ 減少廢棄物外運 **{phys['waste_reduction_ton']}** 公噸")
        if phys.get("cement_reduction_ton", 0):
            phys_lines.append(f"🏗️ 減少水泥等建材 **{phys['cement_reduction_ton']}** 公噸")
        if phys.get("other_benefit_note", ""):
            phys_lines.append(f"📝 其他效益：{phys['other_benefit_note']}")
        if phys_lines:
            st.markdown("**📐 工程量體縮減及其他效益：**")
            for line in phys_lines:
                st.markdown(f"- {line}")

        heat_resp = state.get("heat_safety_response", "")
        heat_note = state.get("heat_safety_note", "")
        if heat_resp and heat_resp != "不適用":
            heat_msg = f"本案另具施工管理型調適考量：已回應高溫作業調適提醒（回應狀態：{heat_resp}，不列入氣候預算總額）。"
            if heat_note:
                heat_msg += f" {heat_note}"
            st.markdown(f"**🌡️ 成果摘要第三層補充：** {heat_msg}")

        # 補充說明
        if state.get("user_note", ""):
            st.markdown(f"**📝 補充說明：** {state.user_note}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart:
        # ── 氣候預算金額顯示 ────────────────────────────────────
        st.markdown(f"""
        <div class="budget-display" style="margin-bottom:0.5rem">
            <div class="label">氣候變遷相關經費</div>
            <div class="amount">{fmt_twd(climate_total)}</div>
            <div style="font-size:0.9rem;opacity:0.85;margin-top:0.3rem">氣候預算占比 {climate_ratio:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Alert box（依計畫總經費判定隱含碳潛力）
        level = alert["level"]
        alert_class = {"extreme": "alert-purple", "red": "alert-red",
                       "yellow": "alert-yellow", "green": "alert-green"}.get(level, "alert-green")
        st.markdown(
            f'<div class="{alert_class}">'
            f'<b>{alert["label"]}</b><br>'
            f'<span style="font-size:0.82rem;">{alert["desc"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Phase 1：信心分數面板 ────────────────────────────────
        confidence = compute_confidence(
            state.kw_matches,
            state.manual_override,
            state.budget,
            state.item_budgets,
        )
        conf_color_map = {"high": "#f0fdf4", "medium": "#fffbf0", "low": "#fff5f5"}
        conf_border_map = {"high": "#27ae60", "medium": "#f39c12", "low": "#e74c3c"}
        conf_bg    = conf_color_map[confidence["level"]]
        conf_bdr   = conf_border_map[confidence["level"]]

        reasons_html = "".join(
            f'<div style="font-size:0.78rem;color:#444;padding:0.2rem 0;'
            f'border-bottom:1px solid rgba(0,0,0,0.06);">'
            f'• {r}</div>'
            for r in confidence["reasons"]
        )
        st.markdown(
            f'<div class="confidence-summary" style="border-left:4px solid {conf_bdr};background:{conf_bg};">'
            f'<div style="font-weight:700;font-size:0.88rem;color:#333;margin-bottom:0.4rem;">'
            f'📊 關鍵字信心評估</div>'
            f'{confidence["badge_html"]}'
            f'<div style="font-size:0.8rem;color:#555;margin-top:0.4rem;">{confidence["desc"]}</div>'
            f'<div style="margin-top:0.5rem;">{reasons_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── 工程減量資訊完整度（有勾選減量工項時才顯示）────────────
        reduction_completeness = compute_reduction_completeness(
            state.item_budgets,
            state.get("physical_reductions", {}),
        )
        if reduction_completeness is not None:
            rc = reduction_completeness
            rc_color_map = {"high": "#f0fdf4", "low": "#fff5f5"}
            rc_border_map = {"high": "#27ae60", "low": "#e74c3c"}
            rc_bg  = rc_color_map[rc["level"]]
            rc_bdr = rc_border_map[rc["level"]]
            rc_reasons_html = "".join(
                f'<div style="font-size:0.78rem;color:#444;padding:0.2rem 0;'
                f'border-bottom:1px solid rgba(0,0,0,0.06);">'
                f'• {r}</div>'
                for r in rc["reasons"]
            )
            st.markdown(
                f'<div class="confidence-summary" style="border-left:4px solid {rc_bdr};background:{rc_bg};margin-top:0.5rem;">'
                f'<div style="font-weight:700;font-size:0.88rem;color:#333;margin-bottom:0.4rem;">'
                f'📐 工程減量資訊完整度</div>'
                f'{rc["badge_html"]}'
                f'<div style="font-size:0.8rem;color:#555;margin-top:0.4rem;">{rc["desc"]}</div>'
                f'<div style="margin-top:0.5rem;">{rc_reasons_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── 氣候行動加分提示（純展示，折疊說明，不點選不輸出）
    st.caption(EXPANDER_HINT_TEXT)
    with st.expander("💡 氣候行動加分提示（展開閱讀）", expanded=False):
        st.markdown(
            "以下是各部會工程減碳指引與氣候政策中，**難以工程金額量化但具重要氣候效益**的行動。"
            "若您的計畫內容或未來規劃符合其中項目，代表計畫的氣候加值程度更高，"
            "建議於補充說明欄位中簡要描述。"
        )
        qualitative_options = UI.get("qualitative_factors", [])
        green_options = CONFIG.get("green_spending_category", [])
        col_q1, col_q2 = st.columns(2)
        for qi, qopt in enumerate(qualitative_options):
            with (col_q1 if qi % 2 == 0 else col_q2):
                st.markdown(f"- {qopt}")
        if green_options:
            st.markdown("**📊 可對接的中央綠色預算支出分類：**")
            for gopt in green_options:
                st.markdown(f"- {gopt}")

    # ── 補充說明（選填，同步至試算表 備註欄）
    st.markdown("**📝 補充說明（選填）**")
    st.caption("可填入表單無法正確量化、需額外說明的事項，例如：符合上方加分提示的具體執行內容、特殊工法說明、跨局處協調事項等。")
    user_note = st.text_area(
        "補充說明",
        value=st.session_state.get("user_note", ""),
        placeholder="例：本案護岸工程規劃採用砌石護岸（自然解方），並預計在施工期間取用附近污水廠放流水作為工程用水……",
        height=100,
        label_visibility="collapsed",
        key="user_note_input",
    )
    st.session_state.user_note = user_note

    # Export section
    st.markdown("---")
    st.markdown('<div class="section-title">📤 匯出評估報告</div>', unsafe_allow_html=True)

    export_payload = {
        "case_name": state.case_name,
        "dept": state.dept,
        "budget": state.budget,
        "manual_override": state.manual_override,
        "kw_matches": state.kw_matches,
        "selected_categories": state.selected_categories,
        "selected_sub_categories": state.selected_sub_categories,
        "item_budgets": state.item_budgets,
        "engineering_guideline_type": state.engineering_guideline_type,
        "physical_reductions": state.get("physical_reductions", {}),
        "user_note": state.get("user_note", ""),
        "heat_safety_prompt_triggered": state.get("heat_safety_prompt_triggered", False),
        "heat_safety_response": state.get("heat_safety_response", ""),
        "heat_safety_note": state.get("heat_safety_note", ""),
        "preset_reference": state.get("preset_reference", {}),
    }
    export_data = generate_export_json(export_payload)

    # Use stable user-input payload for sync gating (exclude volatile uid/timestamp)
    export_signature = hashlib.md5(
        json.dumps(export_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if st.session_state.sync_signature != export_signature:
        st.session_state.sync_done = False
        st.session_state.sync_message = ""
        st.session_state.sync_signature = export_signature

    sheet_target = get_google_sheet_target()
    st.markdown("**步驟 1：先同步到預設 Google 試算表**")
    # if sheet_target.get("spreadsheet_id"):
        # st.caption(
        #     f"預設同步目標：`{sheet_target['spreadsheet_id']}` / 分頁 `{sheet_target['worksheet_name']}`"
        # )
    webhook_ready = is_sheet_sync_ready()
    if not webhook_ready:
        st.warning("⚠️ 尚未完成 Google 試算表同步設定（需 webhook 或 gcp_service_account + google_sheet_id），目前僅可下載本地報告。")
        st.session_state.sync_done = True
    if st.button("☁️ 送出結果並同步 Google 試算表", use_container_width=True, type="primary", disabled=not webhook_ready):
        ok, msg = sync_to_google_sheet(export_data)
        st.session_state.sync_done = ok
        st.session_state.sync_message = msg

    if st.session_state.sync_message:
        if st.session_state.sync_done:
            if sheet_target.get("spreadsheet_id"):
                st.markdown(
                    f"✅ 已完成同步：已直接寫入[試算表](https://docs.google.com/spreadsheets/d/{sheet_target['spreadsheet_id']}/edit)"
                )
            else:
                st.success(f"✅ 已完成同步：{st.session_state.sync_message}")
        else:
            st.error(f"❌ 同步失敗：{st.session_state.sync_message}")

    st.markdown("**步驟 2：同步成功後可下載報告**")

    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

    rows = []
    category_labels = format_category_labels(state.selected_categories)
    sub_category_labels = format_sub_category_labels(state.selected_sub_categories)
    phys = state.get("physical_reductions", {})
    preset_ref = state.get("preset_reference", {})
    phys_parts = []
    if phys.get("soil_reduction_ton", 0):
        phys_parts.append(f"減少土方購置 {phys['soil_reduction_ton']} 公噸")
    if phys.get("waste_reduction_ton", 0):
        phys_parts.append(f"減少廢棄物外運 {phys['waste_reduction_ton']} 公噸")
    if phys.get("cement_reduction_ton", 0):
        phys_parts.append(f"減少水泥等建材 {phys['cement_reduction_ton']} 公噸")
    if phys.get("other_benefit_note", ""):
        phys_parts.append(phys["other_benefit_note"])
    phys_text = "；".join(phys_parts)

    for ib in state.item_budgets:
        item_ratio = round(ib["amount"] / state.budget * 100, 1) if state.budget else 0
        rows.append({
            "評估日期"          : datetime.now(tz=TZ_TAIPEI).strftime("%Y-%m-%d"),
            "案件編號"          : export_data["project_metadata"]["uid"],
            "標案名稱"          : state.case_name,
            "主辦單位"          : state.dept,
            "決標金額"          : state.budget,
            "氣候預算合計"      : climate_total,
            "氣候預算比例%"     : round(climate_ratio, 1),
            "計畫類別"          : category_labels,
            "細項分類"          : sub_category_labels,
            "氣候工項"          : ib["label"],
            "工項金額"          : ib["amount"],
            "工項佔總預算%"     : item_ratio,
            "關鍵字信心"        : export_data.get("confidence", {}).get("label", ""),
            "減量資訊完整度"    : (export_data.get("reduction_completeness") or {}).get("label", ""),
            "命中關鍵字"        : "、".join(export_data.get("matched_keywords", [])),
            "工程量體縮減效益"  : phys_text,
            "國家關鍵戰略 (戰略層面 - Why)": preset_ref.get("national_strategy_why", ""),
            "計畫工法類別 (技術層面 - What)": preset_ref.get("methodology_what", ""),
            "氣候屬性 (功能層面 - How)": preset_ref.get("climate_attribute_how", ""),
            "潛在減緩/減碳亮點 (實務細節 - Action A)": preset_ref.get("mitigation_highlight_action_a", ""),
            "潛在調適/韌性亮點 (實務細節 - Action B)": preset_ref.get("adaptation_highlight_action_b", ""),
            "防呆提醒"          : preset_ref.get("foolproof_notice", ""),
            "補充說明"          : state.get("user_note", ""),
        })

    csv_df = pd.DataFrame(rows)
    csv_bytes = csv_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    col_j, col_c = st.columns(2)

    with col_j:
        st.markdown("**📄 JSON 格式（供系統串接）**")
        st.download_button(
            label="⬇️ 下載 JSON 報告",
            data=json_str.encode("utf-8"),
            file_name=f"climate_budget_{datetime.now(tz=TZ_TAIPEI).strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not st.session_state.sync_done,
        )
        with st.expander("預覽 JSON 內容"):
            st.code(json_str, language="json")

    with col_c:
        st.markdown("**📊 CSV 格式（供 Excel 分析）**")
        st.download_button(
            label="⬇️ 下載 CSV 報告",
            data=csv_bytes,
            file_name=f"climate_budget_{datetime.now(tz=TZ_TAIPEI).strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=not st.session_state.sync_done,
        )
        with st.expander("預覽 CSV 內容"):
            st.dataframe(csv_df, use_container_width=True)
    st.markdown("---")
    col_b, col_r = st.columns([1, 3])
    with col_b:
        if st.button("← 返回修改", use_container_width=True):
            go_to_step(3)
    with col_r:
        if st.button("🔄 評估新案件", use_container_width=True, type="primary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#888;font-size:0.78rem;">'
    '彰化縣氣候預算導引式判讀系統 v1.2 · Phase 1 更新：判讀理由面板 · 信心分數 · UID 強化 ｜ 參考資料源：國家第三期溫室氣體階段管制目標與各部門行動方案、工程減碳參考作業指引、國家氣候變遷調適行動計畫'
    '</p>',
    unsafe_allow_html=True
)
