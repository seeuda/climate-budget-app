import json
from collections import Counter

import os

dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "keyword_dictionary.json")
with open(dict_path, encoding="utf-8") as f:
    data = json.load(f)

kws = data["keyword_triggers"]

# 找所有含 053 的條目
print("=== KW_053 相關條目 ===")
matches = [(i, kw) for i, kw in enumerate(kws) if "053" in kw.get("trigger_id", "")]
for i, kw in matches:
    print(f"  Index {i}: id={kw['trigger_id']}, keyword={kw['keyword']}, "
          f"weight={kw['weight']}, cat={kw.get('category_id')}")
    print(f"    suggested: {kw['suggested_item'][:60]}")

# 所有 trigger_id 重複檢查
print("\n=== 全域 trigger_id 重複檢查 ===")
ids = [kw.get("trigger_id", "") for kw in kws]
dupes = [(tid, cnt) for tid, cnt in Counter(ids).items() if cnt > 1]
if dupes:
    print("  發現重複:")
    for tid, cnt in sorted(dupes):
        entries = [(i, kw["keyword"]) for i, kw in enumerate(kws) if kw.get("trigger_id") == tid]
        print(f"    {tid} x{cnt}: {entries}")
else:
    print("  未發現重複 trigger_id（字典 ID 唯一性正常）")

# 確認 SRF 的實際 weight
print("\n=== SRF 關鍵字詳細資訊 ===")
srf_entries = [(i, kw) for i, kw in enumerate(kws) if kw.get("keyword") == "SRF"]
for i, kw in srf_entries:
    print(f"  Index {i}: trigger_id={kw['trigger_id']}, weight={kw['weight']}, "
          f"purity={kw['purity_hint']}, cat={kw.get('category_id')}")
    print(f"    suggested: {kw['suggested_item']}")
    print(f"    learning_tip: {kw.get('learning_tip', '')[:80]}")

print(f"\n總關鍵字數量: {len(kws)}")
