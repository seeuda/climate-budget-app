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
    """簡易命中判斷（含 negative_context 與 context requirement）"""
    keyword = kw_entry["keyword"]
    synonyms = kw_entry.get("synonyms", [])
    neg_ctx = kw_entry.get("negative_context", [])
    require_any = kw_entry.get("require_any_context", [])
    require_all = kw_entry.get("require_all_context", [])
    
    matched = keyword in text or any(s in text for s in synonyms)
    if not matched:
        return False
    # negative_context 排除
    for neg in neg_ctx:
        if neg in text:
            return False
    if require_any and not any(ctx in text for ctx in require_any):
        return False
    if require_all and not all(ctx in text for ctx in require_all):
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
    ("❌ 負向排除", "農業節水灌溉宣導活動", ["KW_109"], "灌溉關鍵字應被排除，但宣導語意可命中 KW_109"),
    
    # --- 新增驗收：邊坡 ---
    ("🆕 新增驗收", "芬園鄉邊坡坡面植生復育工程", ["KW_107"], "邊坡/坡面應命中 KW_107，並有 anti_pattern 警示"),
    
    # --- 新增驗收：遮蔭 ---
    ("🆕 新增驗收", "彰化市騎樓整平與行人遮蔭設施計畫", ["KW_108"], "騎樓/遮蔭應命中 KW_108"),
    
    # --- 新增驗收：辦理活動需氣候語境 ---
    ("🆕 新增驗收", "彰化縣淨零轉型宣導辦理活動", ["KW_131"], "辦理活動需搭配氣候/淨零語境才命中 KW_131"),
    ("❌ 負向排除", "彰化縣文化季辦理活動委託案", [], "非氣候語境的辦理活動不得誤命中 KW_131"),

    # --- 語意閉環驗收：近期實例 ---
    ("🆕 新增驗收", "彰濱離岸風電運維基地(第二期)新建工程", ["KW_132"], "離岸風電工程應命中再生能源相關導引"),
    ("🆕 新增驗收", "彰化縣二林精密機械產業園區第二階段環境影響評估工作委託技術服務案", ["KW_133"], "環境影響評估案應導向 F1 規劃評估類"),
    ("🆕 新增驗收", "114年度彰化縣特定工廠登記相關輔導計畫", ["KW_140"], "特定工廠登記輔導案應觸發低純度潛力檢核"),
    ("🆕 新增驗收", "彰化縣產業脆弱度分析及因應輔導作法委託專業服務案", ["KW_134"], "脆弱度分析案應導向氣候風險/脆弱度調查"),
    
    # --- 新增驗收：高低溫屬於調適潛力概念詞 ---
    ("🆕 新增驗收", "高溫健康風險預警計畫", ["KW_144"], "具健康風險語境的高溫應辨識為可能涉及氣候變遷調適"),
    ("🆕 新增驗收", "辦理本縣遊民高低溫加強關懷措施", ["KW_148"], "高低溫搭配遊民關懷語境應辨識為調適潛力"),
    ("🆕 新增驗收", "極端高溫防護計畫", ["KW_147"], "極端高溫應直接辨識為調適潛力概念詞"),
    ("🆕 新增驗收", "低溫健康風險預警與關懷服務", ["KW_145"], "具健康風險語境的低溫應辨識為可能涉及氣候變遷調適"),
    ("🆕 新增驗收", "農作物寒害防護計畫", ["KW_146"], "寒害應直接辨識為調適潛力概念詞"),
    ("❌ 負向排除", "高溫殺菌設備採購", [], "製程用途的高溫不得命中"),
    ("❌ 負向排除", "低溫殺菌設備採購", [], "製程用途的低溫不得命中"),
    ("❌ 負向排除", "低溫烹調設備採購", [], "烹調用途的低溫不得命中"),
    ("❌ 負向排除", "農業低溫乾燥設備採購", [], "農業加工用途不得以產業詞通過低溫調適語境檢核"),
    ("❌ 負向排除", "極端高溫材料試驗設備採購", [], "極端高溫不得繞過材料試驗排除語境"),
    ("❌ 負向排除", "極端低溫材料試驗設備採購", [], "極端低溫不得繞過材料試驗排除語境"),
    ("❌ 負向排除", "高低溫冷藏物流風險管理系統採購", [], "高低溫不得以風險語境繞過冷藏物流排除條件"),

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
        # 負向測試：不得命中任何關鍵字
        ok = len(hit_ids) == 0

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

# 高溫、低溫僅作為「可能相關」概念提示，不直接判定為氣候預算工項。
for trigger_id in ("KW_144", "KW_145", "KW_146", "KW_147", "KW_148"):
    trigger = kw_index[trigger_id]
    assert trigger.get("match_type") == "concept_trigger"
    assert trigger.get("purity_hint") == "P4_LOW"
    assert trigger.get("category_id") == "G" and trigger.get("sub_id") == "G3"

assert fail_count == 0, f"關鍵字回歸測試失敗：{fail_count} 個案例未通過"
