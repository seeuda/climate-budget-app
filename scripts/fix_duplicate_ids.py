"""
修復字典中的重複 trigger_id 問題
找出最大現有 ID，將重複的後半段條目重新編號
"""
import json
import re
import os

dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "keyword_dictionary.json")
with open(dict_path, encoding="utf-8") as f:
    data = json.load(f)

kws = data["keyword_triggers"]

# 找出所有 trigger_id 的最大數字
max_num = 0
for kw in kws:
    tid = kw.get("trigger_id", "")
    m = re.match(r"KW_(\d+)$", tid)
    if m:
        max_num = max(max_num, int(m.group(1)))

print(f"目前最大 trigger_id 編號: KW_{max_num:03d}")

# 找出重複的 ID（後出現的那一批需要重新編號）
from collections import OrderedDict
seen = {}
duplicates_idx = []  # 需要重新編號的索引

for i, kw in enumerate(kws):
    tid = kw.get("trigger_id", "")
    if tid in seen:
        duplicates_idx.append(i)
    else:
        seen[tid] = i

print(f"需要重新編號的條目: {len(duplicates_idx)} 個")
for i in duplicates_idx:
    kw = kws[i]
    print(f"  Index {i}: {kw['trigger_id']} → 「{kw['keyword']}」")

# 重新編號：從 max_num+1 開始
next_num = max_num + 1
print(f"\n新編號從 KW_{next_num:03d} 開始")

for i in duplicates_idx:
    old_id = kws[i]["trigger_id"]
    new_id = f"KW_{next_num:03d}"
    kws[i]["trigger_id"] = new_id
    print(f"  {old_id} (「{kws[i]['keyword']}」) → {new_id}")
    next_num += 1

# 寫回
with open(dict_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n完成！共修復 {len(duplicates_idx)} 個重複 ID。最終最大 ID: KW_{next_num-1:03d}")

# 驗證
with open(dict_path, encoding="utf-8") as f:
    data2 = json.load(f)
kws2 = data2["keyword_triggers"]
from collections import Counter
ids2 = [kw.get("trigger_id") for kw in kws2]
dupes2 = [(t, c) for t, c in Counter(ids2).items() if c > 1]
if dupes2:
    print(f"警告：仍有重複: {dupes2}")
else:
    print("驗證通過：所有 trigger_id 現在唯一！")
print(f"總關鍵字數量: {len(kws2)}")
