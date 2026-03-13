"""
彰化縣氣候預算導引式判讀系統
Climate Budget Assessment Tool for Changhua County Government
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
import io
from urllib import request, error
import hashlib

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="彰化縣氣候預算判讀系統",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load JSON data ─────────────────────────────────────────────────────────────
@st.cache_data
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_json("data/config.json")
LOGIC  = load_json("data/logic_mapping.json")
KWDICT = load_json("data/keyword_dictionary.json")

PARAMS = CONFIG["system_parameters"]
UI     = CONFIG["ui_text"]

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
    padding: 2rem 2.5rem;
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

/* Section headers */
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a4731;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #52b788;
    margin-bottom: 1rem;
}

/* Divider */
hr { border-color: #d4e8d4; }

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
    """Return alert level info dict based on budget."""
    if budget >= PARAMS["extreme_alert_threshold"]:
        return {"level": "extreme", "label": "⛔ 極高風險", "desc": "重大公共建設，強制淨零檢核",
                "color": "#8e44ad", "badge": "🟣"}
    elif budget >= PARAMS["high_alert_threshold"]:
        return {"level": "red", "label": "🔴 高碳影響力計畫", "desc": "金額≥2000萬，強調隱含碳檢核",
                "color": "#e74c3c", "badge": "🔴"}
    elif budget >= PARAMS["medium_alert_threshold"]:
        return {"level": "yellow", "label": "🟡 設施改善重點計畫", "desc": "金額1000萬–2000萬",
                "color": "#f39c12", "badge": "🟡"}
    else:
        return {"level": "green", "label": "🟢 自然碳匯或一般維護", "desc": "金額300萬–1000萬",
                "color": "#2ecc71", "badge": "🟢"}

def detect_keywords(text):
    """Return list of matching keyword triggers from case name."""
    if not text:
        return []
    matches = []
    seen = set()
    for kw in KWDICT["keyword_triggers"]:
        if kw["keyword"] in text and kw["keyword"] not in seen:
            matches.append(kw)
            seen.add(kw["keyword"])
    return matches

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

def get_sub_by_id(cat, sub_id):
    for sub in cat.get("sub_categories", []):
        if sub["id"] == sub_id:
            return sub
    return None

def get_item_by_label(sub, label):
    for item in sub.get("items", []):
        if item.get("label") == label:
            return item
    return None

def generate_export_json(state):
    """Generate the export JSON object."""
    result = {
        "project_metadata": {
            "uid": f"CHC-{datetime.now().strftime('%Y%m%d%H%M')}",
            "name": state.get("case_name", ""),
            "dept": state.get("dept", ""),
            "total_budget": state.get("budget", 0),
            "is_manual_override": state.get("manual_override", False),
            "assessment_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "climate_assessment": {
            "category": state.get("selected_category", ""),
            "sub_category": state.get("selected_sub", ""),
            "selected_items": state.get("item_budgets", []),
            "alert_level": get_alert_level(state.get("budget", 0))["label"],
        },
        "climate_budget_total": sum(
            i.get("amount", 0) for i in state.get("item_budgets", [])
        ),
        "impact_level": get_alert_level(state.get("budget", 0))["level"],
        "assessment_metadata": {
            "engineering_guideline_type": state.get("engineering_guideline_type", ""),
            "green_spending_category": state.get("green_spending_category", []),
            "qualitative_factors": state.get("qualitative_factors", []),
        },
    }
    return result


def get_google_sheet_webhook_url():
    """Get Google Sheet webhook URL from Streamlit secrets or config."""
    secret_url = st.secrets.get("google_sheet_webhook_url")
    if secret_url:
        return secret_url
    return CONFIG.get("integrations", {}).get("google_sheet_webhook_url", "")


def get_google_sheet_target():
    """Get default Google Sheet target settings."""
    return {
        "spreadsheet_id": st.secrets.get("google_sheet_id")
        or CONFIG.get("integrations", {}).get("google_sheet_id", ""),
        "worksheet_name": st.secrets.get("google_sheet_worksheet")
        or CONFIG.get("integrations", {}).get("google_sheet_worksheet", "工作表1"),
    }


def sync_to_google_sheet(payload):
    """Send assessment payload to Google Sheet webhook."""
    webhook_url = get_google_sheet_webhook_url()
    if not webhook_url:
        return False, "尚未設定 Google 試算表同步網址（google_sheet_webhook_url）。"

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
    defaults = {
        "step": 0,
        "case_name": "",
        "dept": "",
        "dept_other": "",
        "budget": 0,
        "manual_override": False,
        "kw_matches": [],
        "selected_category": None,
        "selected_sub": None,
        "selected_items": [],
        "item_budgets": [],
        "engineering_guideline_type": "",
        "green_spending_category": [],
        "qualitative_factors": [],
        "sync_done": False,
        "sync_message": "",
        "sync_signature": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🌿 氣候預算系統")
    st.markdown("---")
    st.markdown("**系統說明**")
    st.markdown("""
此工具協助彰化縣各局處承辦人，透過直覺式流程判定計畫與氣候預算的關聯性。

**評估流程：**
1. 輸入計畫基本資訊
2. 系統自動偵測關鍵字
3. 選擇工程類別
4. 勾選氣候相關工項
5. 填寫各工項預算
6. 匯出評估報告
    """)
    st.markdown("---")
    st.markdown("**預算警示門檻**")
    st.markdown("""
- 🟢 300萬–1000萬：自然碳匯/一般維護
- 🟡 1000萬–2000萬：設施改善重點
- 🔴 2000萬–1億：高碳影響力計畫
- 🟣 1億以上：重大建設強制檢核
    """)
    st.markdown("---")
    if st.button("🔄 重新開始", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🌿 彰化縣氣候預算導引式判讀系統</h1>
    <p>Changhua County · Climate Budget Assessment Tool · v1.0</p>
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

# Breadcrumb
bc_parts = ["彰化縣氣候預算系統"]
if st.session_state.case_name:
    bc_parts.append(st.session_state.case_name[:20] + ("…" if len(st.session_state.case_name) > 20 else ""))
if st.session_state.selected_category:
    cat = get_taxonomy_by_id(st.session_state.selected_category)
    if cat:
        bc_parts.append(cat["label"][:15])
if st.session_state.selected_sub:
    cat = get_taxonomy_by_id(st.session_state.selected_category)
    if cat:
        sub = get_sub_by_id(cat, st.session_state.selected_sub)
        if sub:
            bc_parts.append(sub["label"][:15])
st.markdown(f'<div class="breadcrumb">📍 {"  ›  ".join(bc_parts)}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# STEP 0 — 計畫基本資訊
# ═══════════════════════════════════════════════════════════════════

if st.session_state.step == 0:
    st.markdown('<div class="section-title">步驟一：輸入計畫基本資訊</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        case_name = st.text_input(
            "📌 標案名稱",
            value=st.session_state.case_name,
            placeholder="例：彰化縣○○公園綠美化工程",
            help="請輸入公文中的完整標案名稱，系統將自動偵測氣候關鍵字"
        )

        dept_options = ["（請選擇）"] + CONFIG["departments"] + ["其他（自行填寫）"]
        dept_index = 0
        if st.session_state.dept in CONFIG["departments"]:
            dept_index = dept_options.index(st.session_state.dept)
        elif st.session_state.dept and st.session_state.dept not in ("（請選擇）", ""):
            dept_index = dept_options.index("其他（自行填寫）")

        dept = st.selectbox(
            "🏛️ 主辦局處",
            options=dept_options,
            index=dept_index
        )

        dept_other = ""
        if dept == "其他（自行填寫）":
            dept_other = st.text_input(
                "請填寫主辦局處名稱",
                value=st.session_state.dept_other,
                placeholder="例：文化局"
            ).strip()

        budget_input = st.text_input(
            "💰 決標金額（元）",
            value=str(int(st.session_state.budget)) if st.session_state.budget else "",
            placeholder="例：15000000",
            help="請輸入決標金額（純數字，不含逗號）"
        )

    with col2:
        # Keyword detection live preview
        kw_matches = detect_keywords(case_name)
        if case_name and kw_matches:
            st.markdown("**🔍 偵測到的氣候關鍵字**")
            kw_html = '<div class="kw-suggestion">'
            kw_html += "<b>💡 系統自動辨識到以下關鍵字，建議對應工項：</b><br>"
            for kw in kw_matches[:6]:
                kw_html += f'<span class="kw-tag">#{kw["keyword"]}</span> → {kw["suggested_item"]} <code style="background:#eee;padding:1px 4px;border-radius:3px;font-size:0.7rem;">{kw["code"]}</code><br>'
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
            st.markdown('<div class="alert-red">🔴 高碳影響力計畫：本案金額達2,000萬元以上，UI強調「隱含碳」檢核。</div>', unsafe_allow_html=True)
        elif budget_val >= PARAMS["medium_alert_threshold"]:
            st.markdown('<div class="alert-yellow">🟡 設施改善重點：本案金額達1,000萬元以上，請特別注意節能設施評估。</div>', unsafe_allow_html=True)
        elif budget_val >= PARAMS["min_threshold"]:
            st.markdown('<div class="alert-green">🟢 本案符合評估門檻，請繼續完成氣候預算判讀。</div>', unsafe_allow_html=True)

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
    with st.expander("📋 以下樣態計畫建議不需納入評估（點擊展開）"):
        for guideline in UI["exclusion_guidelines"]:
            st.markdown(f"• {guideline}")

    # Proceed button
    selected_dept = dept_other if dept == "其他（自行填寫）" else dept

    can_proceed = (
        case_name.strip()
        and selected_dept not in ("（請選擇）", "")
        and budget_val > 0
        and (budget_val >= PARAMS["min_threshold"] or manual_override)
    )

    if st.button("下一步：選擇計畫及工項類別 →", disabled=not can_proceed, type="primary", use_container_width=True):
        st.session_state.case_name = case_name
        st.session_state.dept = selected_dept
        st.session_state.dept_other = dept_other
        st.session_state.budget = budget_val
        st.session_state.manual_override = manual_override
        st.session_state.kw_matches = kw_matches
        st.session_state.step = 1
        st.rerun()

    if not can_proceed and (case_name or budget_val):
        missing = []
        if not case_name.strip(): missing.append("標案名稱")
        if selected_dept in ("（請選擇）", ""):
            missing.append("主辦局處")
        if not budget_val: missing.append("決標金額")
        if below_threshold and not manual_override: missing.append("確認繼續評估")
        if missing:
            st.caption(f"⚠️ 尚需填寫：{'、'.join(missing)}")

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — 工程類別選擇
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 1:
    st.markdown('<div class="section-title">步驟二：選擇計畫類別（建議先選最接近者，後續可再補充）</div>', unsafe_allow_html=True)

    # Show keyword suggestions
    if st.session_state.kw_matches:
        suggested_cats = list({kw["category_id"] for kw in st.session_state.kw_matches})
        kw_names = [kw["keyword"] for kw in st.session_state.kw_matches]
        st.markdown(f'<div class="kw-suggestion">💡 根據標案名稱中的關鍵字（{"、".join(kw_names[:5])}），系統建議優先檢視以下高亮類別 ↓</div>', unsafe_allow_html=True)
    else:
        suggested_cats = []

    # Category cards — 2 columns
    taxonomy = LOGIC["taxonomy"]
    col1, col2 = st.columns(2)

    for i, cat in enumerate(taxonomy):
        is_suggested = cat["id"] in suggested_cats
        is_selected = st.session_state.selected_category == cat["id"]

        with (col1 if i % 2 == 0 else col2):
            badge = "⭐ 建議類別 · " if is_suggested else ""
            card_style = "highlighted" if is_suggested else ("selected" if is_selected else "")
            selected_mark = "✅ " if is_selected else ""

            if st.button(
                f"{selected_mark}{cat['icon']} {cat['label']}\n{badge}（{cat['description'][:20]}…）",
                key=f"cat_{cat['id']}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_category = cat["id"]
                st.session_state.selected_sub = None
                st.session_state.selected_items = []
                if cat["id"] != "A":
                    st.session_state.engineering_guideline_type = ""
                st.rerun()

    # Sub-category selection
    if st.session_state.selected_category:
        st.markdown("---")
        cat = get_taxonomy_by_id(st.session_state.selected_category)
        st.markdown(f'<div class="section-title">選擇細項分類 — {cat["icon"]} {cat["label"]}</div>', unsafe_allow_html=True)

        suggested_subs = list({kw["sub_id"] for kw in st.session_state.kw_matches
                               if kw.get("category_id") == st.session_state.selected_category})

        subcol1, subcol2 = st.columns(2)
        for j, sub in enumerate(cat.get("sub_categories", [])):
            is_sub_suggested = sub["id"] in suggested_subs
            is_sub_selected = st.session_state.selected_sub == sub["id"]
            with (subcol1 if j % 2 == 0 else subcol2):
                badge = "⭐ " if is_sub_suggested else ""
                selected_mark = "✅ " if is_sub_selected else ""
                if st.button(
                    f"{selected_mark}{badge}{sub['label']}\n📌 {sub['examples'][:30]}",
                    key=f"sub_{sub['id']}",
                    use_container_width=True,
                    type="primary" if is_sub_selected else "secondary"
                ):
                    st.session_state.selected_sub = sub["id"]
                    st.session_state.selected_items = []
                    st.rerun()

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← 返回", use_container_width=True):
            st.session_state.step = 0
            st.rerun()
    with col_next:
        can_next = bool(st.session_state.selected_category)
        if st.button("下一步：勾選氣候工項 →", disabled=not can_next, type="primary", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

# ═══════════════════════════════════════════════════════════════════
# STEP 2 — 工項勾選
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 2:
    st.markdown('<div class="section-title">步驟三：勾選氣候相關工項</div>', unsafe_allow_html=True)

    cat = get_taxonomy_by_id(st.session_state.selected_category)
    sub = get_sub_by_id(cat, st.session_state.selected_sub) if st.session_state.selected_sub else None

    if sub:
        st.markdown(f"**{cat['icon']} {cat['label']}  ›  {sub['label']}**")
        st.caption(f"📌 {sub['examples']}")
        item_sources = [sub]
    else:
        st.markdown(f"**{cat['icon']} {cat['label']}（全部細項工項）**")
        st.caption("📌 已展開該計畫類別下所有細項，請複選適用工項。")
        item_sources = cat.get("sub_categories", [])

    # Suggested items from keywords
    suggested_items_labels = {kw["suggested_item"] for kw in st.session_state.kw_matches}

    st.markdown("**請勾選本案中包含的氣候相關工項（可複選）：**")

    selected_items = list(st.session_state.selected_items)
    rendered = set()
    for src in item_sources:
        if not sub:
            st.markdown(f"**• {src['label']}**")
        for item in src["items"]:
            if item["label"] in rendered:
                continue
            rendered.add(item["label"])
            is_suggested = item["label"] in suggested_items_labels or any(
                kw["suggested_item"] == item["label"] for kw in st.session_state.kw_matches
            )
            is_checked = item["label"] in selected_items

            col_chk, col_info = st.columns([1, 8])
            with col_chk:
                checked = st.checkbox("", value=is_checked, key=f"item_{item['label']}")
            with col_info:
                star = "⭐ " if is_suggested else ""
                codes_html = " ".join([f'<span class="code-badge">{c}</span>' for c in item.get("mitigation_codes", []) + item.get("adaptation_codes", [])])
                alert_html = f'<span style="color:#e74c3c;font-size:0.78rem;"> ⚠️ {item["alert"]}</span>' if item.get("alert") else ""
                st.markdown(
                    f'{star}**{item["label"]}** {codes_html}{alert_html}<br>'
                    f'<span style="font-size:0.78rem;color:#666;">📋 {item["policy"]}</span>',
                    unsafe_allow_html=True
                )

            if checked and item["label"] not in selected_items:
                selected_items.append(item["label"])
            elif not checked and item["label"] in selected_items:
                selected_items.remove(item["label"])

    st.session_state.selected_items = selected_items

    if not selected_items:
        st.caption("本步驟可先略過，下一步可直接進行預算檢視與補充。")

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← 返回", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("下一步：填寫工項預算 →", type="primary", use_container_width=True):
            # Init item_budgets
            existing = {ib["label"]: ib for ib in st.session_state.item_budgets}
            st.session_state.item_budgets = [
                existing.get(label, {"label": label, "ratio": None, "amount": 0})
                for label in selected_items
            ]
            st.session_state.step = 3
            st.rerun()

# ═══════════════════════════════════════════════════════════════════
# STEP 3 — 預算拆解
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 3:
    st.markdown('<div class="section-title">步驟四：填寫各工項氣候預算</div>', unsafe_allow_html=True)

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

        col_amt, col_calc = st.columns([3, 2])

        with col_amt:
            saved_amount = int(ib.get("amount", 0) or 0)
            clamped_amount = min(max(saved_amount, 0), total_budget)
            amount = st.number_input(
                "工項參考金額（元）",
                min_value=0,
                max_value=total_budget,
                value=clamped_amount,
                step=100000,
                key=f"amt_{idx}"
            )

        with col_calc:
            pct_of_total = amount / total_budget * 100 if total_budget else 0
            st.metric("佔總預算", f"{pct_of_total:.1f}%", delta=fmt_twd(amount))

        updated_items.append({
            "label": label,
            "ratio": round(pct_of_total, 1),
            "amount": int(amount)
        })

        st.markdown("<hr style='margin:0.5rem 0; border-color:#e8f0e8'>", unsafe_allow_html=True)

    st.session_state.item_budgets = updated_items

    # Recalculate for button state
    total_allocated = sum(ib.get("amount", 0) or 0 for ib in updated_items)
    over_budget = total_allocated > total_budget
    all_set = all(ib.get("amount", 0) > 0 for ib in updated_items)

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← 返回", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_next:
        can_next = all_set and not over_budget
        if st.button("下一步：確認並匯出報告 →", disabled=not can_next, type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()
        if not can_next:
            if over_budget:
                st.caption("🚫 工項金額加總超出總預算，請調整。")
            elif not all_set:
                st.caption("⚠️ 請為所有工項設定預算金額。")

# ═══════════════════════════════════════════════════════════════════
# STEP 4 — 確認與匯出
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.step == 4:
    st.markdown('<div class="section-title">步驟五：確認評估結果並匯出</div>', unsafe_allow_html=True)

    state = st.session_state
    alert = get_alert_level(state.budget)
    cat = get_taxonomy_by_id(state.selected_category)
    sub = get_sub_by_id(cat, state.selected_sub) if cat else None

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

**{alert['badge']} 風險等級：** {alert['label']} — {alert['desc']}
        """)

        if cat and sub:
            st.markdown(f"""
**{cat['icon']} 標案類別：** {cat['label']}

**📂 細項分類：** {sub['label']}
            """)

        st.markdown("**✅ 氣候相關工項：**")
        for ib in state.item_budgets:
            pct = ib['amount'] / state.budget * 100 if state.budget else 0
            st.markdown(f"- {ib['label']}：{fmt_twd(ib['amount'])} （{pct:.1f}%）")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart:
        st.markdown(f"""
        <div class="budget-display" style="margin-bottom:0.5rem">
            <div class="label">氣候變遷相關經費</div>
            <div class="amount">{fmt_twd(climate_total)}</div>
            <div style="font-size:0.9rem;opacity:0.85;margin-top:0.3rem">氣候預算占比 {climate_ratio:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Simple progress bar
        st.progress(min(climate_ratio / 100, 1.0), text=f"氣候預算占比 {climate_ratio:.1f}%")

        # Alert box
        level = alert["level"]
        if level == "extreme":
            st.markdown(f'<div class="alert-purple"><b>{alert["label"]}</b><br>{alert["desc"]}</div>', unsafe_allow_html=True)
        elif level == "red":
            st.markdown(f'<div class="alert-red"><b>{alert["label"]}</b><br>{alert["desc"]}</div>', unsafe_allow_html=True)
        elif level == "yellow":
            st.markdown(f'<div class="alert-yellow"><b>{alert["label"]}</b><br>{alert["desc"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-green"><b>{alert["label"]}</b><br>{alert["desc"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-title">🧩 政策對接補充欄位</div>', unsafe_allow_html=True)

    st.session_state.green_spending_category = st.multiselect(
        "綠色預算支出分類（可複選）",
        options=CONFIG.get("green_spending_category", []),
        default=st.session_state.green_spending_category,
        help="對接中央綠色經費四大面向"
    )

    qualitative_options = UI.get("qualitative_factors", [])
    st.session_state.qualitative_factors = st.multiselect(
        "氣候政策加分因子（可複選）",
        options=qualitative_options,
        default=st.session_state.qualitative_factors,
        help="補充難以工程量化但可強化氣候效益的執行方案因子"
    )

    # Export section
    st.markdown("---")
    st.markdown('<div class="section-title">📤 匯出評估報告</div>', unsafe_allow_html=True)

    export_payload = {
        "case_name": state.case_name,
        "dept": state.dept,
        "budget": state.budget,
        "manual_override": state.manual_override,
        "selected_category": state.selected_category,
        "selected_sub": state.selected_sub,
        "item_budgets": state.item_budgets,
        "engineering_guideline_type": state.engineering_guideline_type,
        "green_spending_category": state.green_spending_category,
        "qualitative_factors": state.qualitative_factors,
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
    if sheet_target.get("spreadsheet_id"):
        st.caption(
            f"預設同步目標：`{sheet_target['spreadsheet_id']}` / 分頁 `{sheet_target['worksheet_name']}`"
        )
    webhook_ready = bool(get_google_sheet_webhook_url())
    if not webhook_ready:
        st.warning("⚠️ 尚未設定 Google 試算表同步網址（google_sheet_webhook_url），目前僅可下載本地報告。")
        st.session_state.sync_done = True
    if st.button("☁️ 送出結果並同步 Google 試算表", use_container_width=True, type="primary", disabled=not webhook_ready):
        ok, msg = sync_to_google_sheet(export_data)
        st.session_state.sync_done = ok
        st.session_state.sync_message = msg

    if st.session_state.sync_message:
        if st.session_state.sync_done:
            st.success(f"✅ 已完成同步：{st.session_state.sync_message}")
        else:
            st.error(f"❌ 同步失敗：{st.session_state.sync_message}")

    st.markdown("**步驟 2：同步成功後可下載報告**")

    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

    rows = []
    for ib in state.item_budgets:
        rows.append({
            "評估日期": datetime.now().strftime("%Y-%m-%d"),
            "標案名稱": state.case_name,
            "主辦局處": state.dept,
            "決標金額": state.budget,
            "風險等級": alert["label"],
            "氣候工項": ib["label"],
            "工項金額": ib["amount"],
            "工項比例(%)": round(ib["amount"] / state.budget * 100, 1) if state.budget else 0,
            "氣候預算合計": climate_total,
            "氣候預算比例(%)": round(climate_ratio, 1),
        })

    csv_df = pd.DataFrame(rows)
    csv_bytes = csv_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    col_j, col_c = st.columns(2)

    with col_j:
        st.markdown("**📄 JSON 格式（供系統串接）**")
        st.download_button(
            label="⬇️ 下載 JSON 報告",
            data=json_str.encode("utf-8"),
            file_name=f"climate_budget_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
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
            file_name=f"climate_budget_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
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
            st.session_state.step = 3
            st.rerun()
    with col_r:
        if st.button("🔄 評估新案件", use_container_width=True, type="primary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#888;font-size:0.78rem;">'
    '彰化縣氣候預算導引式判讀系統 v1.0 · 資料源：國家第三期溫室氣體階段管制目標與各部門行動方案'
    '</p>',
    unsafe_allow_html=True
)
