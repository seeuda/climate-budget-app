# 關鍵字分層回歸測試清單（v1.3.1）

此清單提供本地人工驗證用，對照：

- **改版前**：`6a5abd4`（未導入 concept_trigger 分層）
- **改版後**：`v1.3.1`（導入 concept_trigger + synonyms/negative_context）

---

## 測試案例（12 句）

> 欄位說明：  
> `strong_matches` / `concept_matches` / `logic_matches` / `confidence_score` / `是否推薦工項` / `是否顯示概念提示`

| # | 標案名稱 | 改版前 | 改版後 |
|---|---|---|---|
| 1 | 永續教育推廣計畫 | `strong=['永續']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=[]`, `logic=[]`, `confidence=low`, `推薦=否`, `概念提示=否` |
| 2 | 永續觀光活動 | `strong=['永續']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=[]`, `logic=[]`, `confidence=low`, `推薦=否`, `概念提示=否` |
| 3 | 氣候變遷調適研究案 | `strong=['氣候變遷','調適']`, `concept=[]`, `logic=[]`, `confidence=high`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=['氣候變遷','調適']`, `logic=[]`, `confidence=medium`, `推薦=否`, `概念提示=是` |
| 4 | 調適規劃案 | `strong=['調適']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=['調適']`, `logic=[]`, `confidence=medium`, `推薦=否`, `概念提示=是` |
| 5 | 低碳宣導活動 | `strong=['低碳']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=[]`, `logic=[]`, `confidence=low`, `推薦=否`, `概念提示=否` |
| 6 | 溫室氣體盤查案 | `strong=['溫室氣體']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=['溫室氣體']`, `logic=[]`, `confidence=medium`, `推薦=否`, `概念提示=是` |
| 7 | 韌性提升工程 | `strong=[]`, `concept=[]`, `logic=[]`, `confidence=low`, `推薦=否`, `概念提示=否` | `strong=[]`, `concept=['調適']`, `logic=[]`, `confidence=medium`, `推薦=否`, `概念提示=是` |
| 8 | LED路燈汰換工程 | `strong=['LED','路燈']`, `concept=[]`, `logic=[]`, `confidence=high`, `推薦=是`, `概念提示=否` | `strong=['LED','路燈']`, `concept=[]`, `logic=[]`, `confidence=high`, `推薦=是`, `概念提示=否` |
| 9 | 排水工程改善計畫 | `strong=['排水']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=['排水']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` |
| 10 | 光電設置案 | `strong=['光電']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=['光電']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` |
| 11 | 公務車租賃汰換計畫 | `strong=[]`, `concept=[]`, `logic=['租賃/公務車']`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=[]`, `logic=['租賃/公務車']`, `confidence=medium`, `推薦=是`, `概念提示=否` |
| 12 | 一般道路修復工程 | `strong=['修復']`, `concept=[]`, `logic=[]`, `confidence=medium`, `推薦=是`, `概念提示=否` | `strong=[]`, `concept=[]`, `logic=[]`, `confidence=low`, `推薦=否`, `概念提示=否` |

---

## 建議回歸重點（邊界）

1. 永續教育 / 永續觀光是否過度排除（目前會被 `negative_context` 排除）。  
2. 調適研究/規劃是否保留「概念相關」但不直接推工項（目前符合）。  
3. 低碳宣導活動是否避免誤判為可直接編列工項（目前符合）。  
4. 韌性同義詞是否正確導向 `調適` concept trigger（目前符合）。  

---

## 泛工程詞 strong trigger 盤點（v1.3.2）

| 關鍵字 | v1.3.1 狀態 | v1.3.2 狀態 | 調整策略 |
|---|---|---|---|
| 修復 | strong_trigger | concept_trigger + `negative_context=['道路','路面']` | 避免一般道路修復直接推薦工項 |
| 新建 | strong_trigger | concept_trigger | 保留為入口提示，不直接推工項 |
| 改善 | 未建 trigger | 未建 trigger | 由 anti-pattern 與組合訊號承接 |
| 整修 | 未建 trigger | 未建 trigger | 維持不作直接觸發詞 |
