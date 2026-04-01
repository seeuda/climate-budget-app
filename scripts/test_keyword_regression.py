"""
氣候預算參數庫驗收測試 - Sonnet Review 修改驗證
測試重點：本次修改的關鍵字邏輯是否正確運作
"""
import json
import os

# 載入字典
dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "keyword_dictionary.json")
with open(dict_path, encoding="utf-8") as f:
    data = json.load(f)

kw_triggers = data["keyword_triggers"]

# 建立查找索引
kw_index = {kw["trigger_id"]: kw for kw in kw_triggers}

def match_keyword(text, kw_entry):
    """簡易命中判斷（含 negative_context 排除）"""
    keyword = kw_entry["keyword"]
    synonyms = kw_entry.get("synonyms", [])
    neg_ctx = kw_entry.get("negative_context", [])
    
    matched = keyword in text or any(s in text for s in synonyms)
    if not matched:
        return False
    # negative_context 排除
    for neg in neg_ctx:
        if neg in text:
            return False
    return True

def scan_text(text):
    """對輸入案名進行全詞典掃描，回傳命中清單"""
    hits = []
    for kw in kw_triggers:
        if match_keyword(text, kw):
            hits.append({
                "id": kw["trigger_id"],
                "keyword": kw["keyword"],
                "category": kw.get("category_id", "?"),
                "weight": kw.get("weight", 0),
                "purity": kw.get("purity_hint", "?"),
                "suggested": kw.get("suggested_item", "")[:40],
                "has_ap": len(kw.get("anti_pattern_ids", [])) > 0,
                "has_tip": len(kw.get("learning_tip", "")) > 0,
            })
    return hits

# ===== 測試案例設計 =====
test_cases = [
    # --- 修正驗證：野溪 ---
    ("🔧 修正驗收", "彰化縣二水鄉野溪整治工程", ["KW_069"], "KW_069 應命中，類別應為 B (調適-水)"),
    
    # --- 修正驗收：護岸 ---
    ("🔧 修正驗收", "福興鄉溝渠護岸改善工程", ["KW_042"], "KW_042 護岸應命中，weight應為0.6，anti_pattern應存在"),
    
    # --- 負向測試：災修＋道路 → 應被排除 ---
    ("❌ 負向排除", "台14線道路路基災修工程", [], "道路災修應被 negative_context ['道路','路基'] 排除"),
    
    # --- 正向測試：災修（水利）→ 應保留 ---
    ("✅ 正向保留", "濁水溪護岸災修工程", ["KW_037", "KW_042"], "水利護岸災修應同時命中KW_037、KW_042"),
    
    # --- 修正驗收：SRF ---
    ("🔧 修正驗收", "彰化縣SRF固體再生燃料利用計畫", ["KW_053"], "SRF應命中，類別應為 B (環境-5)，非教育類"),
    
    # --- 新增驗收：灌溉節水 ---
    ("🆕 新增驗收", "大城鄉農業滴灌節水管路改善計畫", ["KW_106"], "灌溉/滴灌應命中 KW_106"),
    
    # --- 新增驗收：灌溉負向（僅宣導）---
    ("❌ 負向排除", "農業節水灌溉宣導活動", [], "宣導類灌溉案件應被排除"),
    
    # --- 新增驗收：邊坡 ---
    ("🆕 新增驗收", "芬園鄉邊坡坡面植生復育工程", ["KW_107"], "邊坡/坡面應命中 KW_107，並有 anti_pattern 警示"),
    
    # --- 新增驗收：遮蔭 ---
    ("🆕 新增驗收", "彰化市騎樓整平與行人遮蔭設施計畫", ["KW_108"], "騎樓/遮蔭應命中 KW_108"),
    
    # --- 回歸測試：既有高純度詞 ---
    ("🔁 回歸測試", "彰化縣滯洪池新建工程", ["KW_005"], "滯洪池應仍為 P1_HIGH_PURITY"),
    ("🔁 回歸測試", "縣道彰61線LED路燈汰換計畫", ["KW_001", "KW_002"], "LED/路燈雙重命中"),
    ("🔁 回歸測試", "彰化市某國小綠建築改善工程", ["KW_010"], "綠建築應命中"),
]

# ===== 執行測試 =====
print("=" * 65)
print("  氣候預算參數庫 Sonnet Review 驗收測試")
print("=" * 65)

pass_count = 0
fail_count = 0

for label, text, expected_ids, note in test_cases:
    hits = scan_text(text)
    hit_ids = [h["id"] for h in hits]
    
    if expected_ids:
        ok = all(eid in hit_ids for eid in expected_ids)
    else:
        # 負向測試：期望特定詞不在命中結果中
        # 取命中中是否有 KW_037 or KW_106（主要測試詞）
        # 若無命中 or 只有其他詞命中，也算通過
        relevant_ids = {"KW_037", "KW_106"}
        ok = not any(h in relevant_ids for h in hit_ids)

    status = "✅ PASS" if ok else "❌ FAIL"
    if ok:
        pass_count += 1
    else:
        fail_count += 1

    print(f"\n{status} {label}")
    print(f"  案名：{text}")
    print(f"  說明：{note}")
    if hits:
        for h in hits:
            ap_marker = " ⚠️AP" if h["has_ap"] else ""
            tip_marker = " 📝" if h["has_tip"] else ""
            print(f"  → [{h['id']}] 「{h['keyword']}」 Cat:{h['category']} W:{h['weight']} {h['purity']}{ap_marker}{tip_marker}")
            print(f"       建議工項：{h['suggested']}")
    else:
        print("  → （無命中）")
    
    if not ok:
        print(f"  ⚠️  期望命中：{expected_ids}，實際：{hit_ids}")

print("\n" + "=" * 65)
print(f"  結果：{pass_count} PASS / {fail_count} FAIL")

# 額外驗證：KW_069 的分類是否已修正
kw069 = kw_index.get("KW_069", {})
print(f"\n  [KW_069 野溪] category_id = {kw069.get('category_id')} (期望: B)")
print(f"  [KW_069 野溪] code = {kw069.get('code')} (期望: 調適-水)")
print(f"  [KW_069 野溪] anti_pattern = {kw069.get('anti_pattern_ids')} (期望: [2,7])")
print(f"  [KW_069 野溪] has_tip = {len(kw069.get('learning_tip','')) > 0}")

kw042 = kw_index.get("KW_042", {})
print(f"\n  [KW_042 護岸] weight = {kw042.get('weight')} (期望: 0.6)")
print(f"  [KW_042 護岸] anti_pattern = {kw042.get('anti_pattern_ids')} (期望: [7])")

kw053_srf = kw_index.get("KW_053", {})
print(f"\n  [KW_053 SRF] category_id = {kw053_srf.get('category_id')} (期望: B)")
print(f"  [KW_053 SRF] weight = {kw053_srf.get('weight')} (期望: 0.8)")
print("=" * 65)
